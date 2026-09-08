// SPDX-License-Identifier: MIT
// Native Installed YAML Data observations traverse generated config bridge DTOs.

namespace installed_config = classic::config;

/// Converts a closed generated bridge enum into the shared semantic token, rejecting unknown values.
template <typename Enum>
std::string installed_token(Enum value, std::initializer_list<std::pair<Enum, std::string_view>> tokens) {
    for (const auto& [variant, token] : tokens) {
        if (value == variant) {
            return std::string(token);
        }
    }
    throw RunnerError("unknown Installed YAML Data bridge enum variant");
}

/// Projects the selected or diagnosed installed file role.
std::string installed_role(installed_config::InstalledYamlDataRole role) {
    using E = installed_config::InstalledYamlDataRole;
    return installed_token(role, {{E::Main, "main"}, {E::Game, "game"}});
}

/// Projects update-eligible error attribution; Local Ignore failures have no Main/Game selection role.
json installed_load_role(installed_config::InstalledYamlDataLoadRole role) {
    using E = installed_config::InstalledYamlDataLoadRole;
    if (role == E::LocalIgnore) {
        return nullptr;
    }
    return installed_token(role, {{E::Main, "main"}, {E::Game, "game"}});
}

/// Projects candidate precedence from the actual generated enum.
std::string installed_provenance(installed_config::InstalledYamlDataProvenance provenance) {
    using E = installed_config::InstalledYamlDataProvenance;
    return installed_token(provenance, {{E::Updated, "updated"}, {E::Previous, "previous"}, {E::Bundled, "bundled"}});
}

/// Projects diagnostic vocabulary independently of its reworkable display message.
std::string installed_diagnostic_kind(installed_config::InstalledYamlDataDiagnosticKind kind) {
    using E = installed_config::InstalledYamlDataDiagnosticKind;
    return installed_token(kind, {{E::CacheUnavailable, "cache_unavailable"},
                                  {E::Missing, "missing"},
                                  {E::Read, "read"},
                                  {E::InvalidUtf8, "invalid_utf8"},
                                  {E::Parse, "parse"},
                                  {E::InvalidSchema, "invalid_schema"},
                                  {E::IncompatibleSchema, "incompatible_schema"},
                                  {E::InvalidRoleData, "invalid_role_data"},
                                  {E::LocalIgnoreGenerated, "local_ignore_generated"},
                                  {E::LocalIgnoreReset, "local_ignore_reset"}});
}

/// Projects the requested game identity returned by an immutable public handle.
std::string installed_game(installed_config::ExplicitYamlDataGameId game) {
    using E = installed_config::ExplicitYamlDataGameId;
    return installed_token(
        game,
        {{E::Fallout4, "Fallout4"}, {E::Fallout4VR, "Fallout4VR"}, {E::Skyrim, "Skyrim"}, {E::Starfield, "Starfield"}});
}

/// Projects registered game-data role separately from the requested VR game identity.
std::string installed_game_role(installed_config::InstalledYamlDataGameRole role) {
    using E = installed_config::InstalledYamlDataGameRole;
    return installed_token(role, {{E::Fallout4, "Fallout4"}});
}

/// Attaches the contract's known role path to a retained CXX content identity.
json installed_identity(const installed_config::YamlDataContentIdentityDto& identity, const std::string& path) {
    return json{{"path", path}, {"sha256", owned_string(identity.sha256)}, {"byteLength", identity.byte_len}};
}

/// Reconstructs a selected path from typed role and provenance because the CXX file DTO exposes no path.
json installed_file(const installed_config::InspectedYamlDataFileDto& file) {
    const std::string role = installed_role(file.role);
    const std::string provenance = installed_provenance(file.provenance);
    const std::string name = role == "main" ? "CLASSIC Main.yaml" : "CLASSIC Fallout4.yaml";
    const std::string path =
        (provenance == "bundled" ? "installation/CLASSIC Data/databases/" : "cache/CLASSIC/yaml-cache/") + name +
        (provenance == "previous" ? ".prev" : "");
    return json{
        {"role", role},
        {"provenance", provenance},
        {"schemaVersion", owned_string(file.schema_version)},
        {"identity", json{{"path", path}, {"sha256", owned_string(file.sha256)}, {"byteLength", file.byte_len}}}};
}

/// Copies ordered diagnostic attribution directly from the public bridge DTOs.
json installed_diagnostics(const rust::Vec<installed_config::InstalledYamlDataDiagnosticDto>& diagnostics,
                           const fs::path& root) {
    json result = json::array();
    for (const auto& diagnostic : diagnostics) {
        result.push_back(json{
            {"role", diagnostic.has_role ? json(installed_role(diagnostic.role)) : json(nullptr)},
            {"candidate", diagnostic.has_candidate ? json(installed_provenance(diagnostic.candidate)) : json(nullptr)},
            {"path",
             diagnostic.has_path ? json(relative_path(root, fs::path(owned_string(diagnostic.path)))) : json(nullptr)},
            {"kind", installed_diagnostic_kind(diagnostic.kind)}});
    }
    return result;
}

/// Writes centrally owned UTF-8 fixture bytes, with paths confined to this scenario.
void installed_write_files(const fs::path& root, const json& files) {
    for (const auto& [relative, content] : files.items()) {
        const auto path = runtime_path(root, relative, "Installed YAML Data fixture path");
        fs::create_directories(path.parent_path());
        std::ofstream output(path, std::ios::binary | std::ios::trunc);
        const std::string bytes = content.get<std::string>();
        output.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
        output.close();
        if (!output) {
            throw RunnerError("cannot write Installed YAML Data fixture: " + path.string());
        }
    }
}

/// Hashes every actual final file independently of the bridge's retained content identities.
json installed_files(const fs::path& root) {
    std::map<std::string, json> ordered;
    for (const auto& entry : fs::recursive_directory_iterator(root)) {
        if (entry.is_regular_file()) {
            std::ifstream input(entry.path(), std::ios::binary);
            if (!input) {
                throw RunnerError("cannot read observed Installed YAML Data file: " + entry.path().string());
            }
            const std::vector<std::uint8_t> bytes{std::istreambuf_iterator<char>(input),
                                                  std::istreambuf_iterator<char>()};
            if (input.bad()) {
                throw RunnerError("cannot finish reading observed Installed YAML Data file");
            }
            const std::string path = relative_path(root, entry.path());
            ordered.emplace(path,
                            json{{"path", path}, {"sha256", Sha256::digest(bytes)}, {"byteLength", bytes.size()}});
        }
    }
    json result = json::array();
    for (auto& [path, identity] : ordered) {
        result.push_back(std::move(identity));
    }
    return result;
}

/// Projects a ready immutable snapshot after optional disk mutation to verify retained ownership.
void installed_snapshot(json& result, const installed_config::InstalledYamlDataSnapshot& snapshot,
                        const fs::path& root) {
    using E = installed_config::LocalIgnoreYamlDataState;
    const auto state = installed_token(installed_config::installed_yaml_data_snapshot_local_ignore_state(snapshot),
                                       {{E::Existing, "existing"},
                                        {E::Generated, "generated"},
                                        {E::ProceedWithoutIgnore, "proceed_without_ignore"},
                                        {E::ResetToDefault, "reset_to_default"}});
    result["outcome"] = "ready";
    result["game"] = installed_game(installed_config::installed_yaml_data_snapshot_game(snapshot));
    result["gameDataRole"] = installed_game_role(installed_config::installed_yaml_data_snapshot_game_role(snapshot));
    result["main"] = installed_file(installed_config::installed_yaml_data_snapshot_main(snapshot));
    result["gameFile"] = installed_file(installed_config::installed_yaml_data_snapshot_game_file(snapshot));
    result["localIgnore"] = json{
        {"state", state},
        {"identity", installed_identity(installed_config::installed_yaml_data_snapshot_local_ignore_identity(snapshot),
                                        "installation/CLASSIC Data/CLASSIC Ignore.yaml")}};
    result["diagnostics"] =
        installed_diagnostics(installed_config::installed_yaml_data_snapshot_diagnostics(snapshot), root);
    const auto data = installed_config::installed_yaml_data_snapshot_yaml_data(snapshot);
    json ignore = json::array();
    for (const auto& value : installed_config::yaml_data_ignore_list(*data)) {
        ignore.push_back(owned_string(value));
    }
    json simplify = json::array();
    for (const auto& value : installed_config::installed_yaml_data_snapshot_simplify_remove_list(snapshot)) {
        simplify.push_back(owned_string(value));
    }
    result["snapshot"] = json{{"classicVersion", std::string(installed_config::yaml_data_classic_version(*data))},
                              {"gameRootName", owned_string(installed_config::yaml_data_get_game_root_name(*data))},
                              {"ignoreList", std::move(ignore)},
                              {"simplifyRemoveList", std::move(simplify)}};
}

/// Runs one input-only Installed YAML Data scenario through the native generated config bridge.
json execute_installed_yaml_data_scenario(const json& plan, const json& scenario) {
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),
                                 scenario.at("id").get<std::string>());
    const fs::path& root = temporary.path();
    RuntimeEnvironment environment(root, "cache");
    const std::string reference = scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references = scenario.at("fixtureRefs");
    if (std::find(references.begin(), references.end(), reference) == references.end()) {
        throw RunnerError("Installed YAML Data fixture is not declared by the scenario");
    }
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const json fixture = json::parse(stream);
    std::optional<std::string> backup_alias;
    installed_write_files(root, fixture.at("files"));
    fs::create_directories(root / "installation");
    using G = installed_config::ExplicitYamlDataGameId;
    const std::string requested_game = fixture.at("game").get<std::string>();
    const auto game = requested_game == "Fallout4"     ? G::Fallout4
                      : requested_game == "Fallout4VR" ? G::Fallout4VR
                      : requested_game == "Skyrim"     ? G::Skyrim
                      : requested_game == "Starfield" ? G::Starfield
                                                      : throw RunnerError("unsupported Installed YAML Data input game");
    json result{{"outcome", "error"},  {"game", nullptr},       {"gameDataRole", nullptr},
                {"main", nullptr},     {"gameFile", nullptr},   {"localIgnore", nullptr},
                {"recovery", nullptr}, {"snapshot", nullptr},   {"diagnostics", json::array()},
                {"error", nullptr},    {"files", json::array()}};
    const std::string installation = (root / "installation").string();
    const std::string operation = fixture.at("operation").get<std::string>();
    if (operation == "inspect") {
        auto pending = installed_config::installed_yaml_data_inspect(installation, game);
        installed_write_files(root, fixture.value("mutations", json::object()));
        const auto status = installed_config::installed_yaml_data_inspection_status(*pending);
        if (status.has_inspection == status.has_error) {
            throw RunnerError("Installed YAML Data inspection violated exclusive status flags");
        }
        if (status.has_error) {
            using E = installed_config::InstalledYamlDataInspectionErrorKind;
            result["error"] =
                json{{"code", installed_token(status.error.kind, {{E::UnsupportedGame, "unsupported_game"},
                                                                  {E::NoUsableSource, "no_usable_source"}})},
                     {"role", status.error.has_role ? json(installed_role(status.error.role)) : json(nullptr)}};
            result["diagnostics"] = installed_diagnostics(status.error.diagnostics, root);
        } else {
            const auto inspection = installed_config::installed_yaml_data_inspection_take(std::move(pending));
            result["outcome"] = "inspected";
            result["game"] = installed_game(installed_config::installed_yaml_data_inspection_game(*inspection));
            result["gameDataRole"] =
                installed_game_role(installed_config::installed_yaml_data_inspection_game_role(*inspection));
            result["main"] = installed_file(installed_config::installed_yaml_data_inspection_main(*inspection));
            result["gameFile"] =
                installed_file(installed_config::installed_yaml_data_inspection_game_file(*inspection));
            result["diagnostics"] =
                installed_diagnostics(installed_config::installed_yaml_data_inspection_diagnostics(*inspection), root);
        }
    } else if (operation == "load") {
        auto pending = installed_config::installed_yaml_data_load(installation, game,
                                                                  fixture.at("selectedGameVersion").get<std::string>());
        installed_write_files(root, fixture.value("mutations", json::object()));
        const auto status = installed_config::installed_yaml_data_load_status(*pending);
        if (static_cast<int>(status.has_snapshot) + static_cast<int>(status.has_recovery_plan) +
                static_cast<int>(status.has_error) !=
            1) {
            throw RunnerError("Installed YAML Data load violated exclusive status flags");
        }
        if (status.has_error) {
            using E = installed_config::InstalledYamlDataLoadErrorKind;
            result["error"] =
                json{{"code", installed_token(status.error.kind,
                                              {{E::UnsupportedGame, "unsupported_game"},
                                               {E::NoUsableSource, "no_usable_source"},
                                               {E::LocalIgnoreRead, "local_ignore_read"},
                                               {E::InvalidSelectedData, "invalid_selected_data"},
                                               {E::LocalIgnoreDefaultInvalid, "local_ignore_default_invalid"},
                                               {E::LocalIgnoreCreate, "local_ignore_create"}})},
                     {"role", status.error.has_role ? json(installed_load_role(status.error.role)) : json(nullptr)}};
            result["diagnostics"] = installed_diagnostics(status.error.diagnostics, root);
        } else if (status.has_snapshot) {
            const auto snapshot = installed_config::installed_yaml_data_load_take_snapshot(std::move(pending));
            installed_snapshot(result, *snapshot, root);
        } else {
            auto recovery = installed_config::installed_yaml_data_load_take_recovery_plan(std::move(pending));
            const std::string path = relative_path(
                root,
                fs::path(owned_string(installed_config::local_ignore_recovery_plan_local_ignore_path(*recovery))));
            result["outcome"] = "recovery_required";
            result["game"] = installed_game(installed_config::local_ignore_recovery_plan_game(*recovery));
            result["gameDataRole"] =
                installed_game_role(installed_config::local_ignore_recovery_plan_game_role(*recovery));
            result["main"] = installed_file(installed_config::local_ignore_recovery_plan_main(*recovery));
            result["gameFile"] = installed_file(installed_config::local_ignore_recovery_plan_game_file(*recovery));
            result["diagnostics"] =
                installed_diagnostics(installed_config::local_ignore_recovery_plan_diagnostics(*recovery), root);
            result["recovery"] = json{
                {"localIgnorePath", path},
                {"malformedIdentity",
                 installed_identity(
                     installed_config::local_ignore_recovery_plan_malformed_local_ignore_identity(*recovery), path)},
                {"defaultIdentity",
                 installed_config::local_ignore_recovery_plan_has_default_local_ignore_identity(*recovery)
                     ? installed_identity(
                           installed_config::local_ignore_recovery_plan_default_local_ignore_identity(*recovery), path)
                     : json(nullptr)},
                {"selectedGameVersion",
                 owned_string(installed_config::local_ignore_recovery_plan_selected_game_version(*recovery))}};
            if (fixture.value("recoveryAction", "") == "proceed") {
                const auto snapshot =
                    installed_config::local_ignore_recovery_plan_proceed_without_ignore(std::move(recovery));
                installed_snapshot(result, *snapshot, root);
                result["outcome"] = "proceeded";
            } else if (fixture.value("recoveryAction", "") == "reset") {
                auto reset = installed_config::local_ignore_recovery_plan_reset_to_default(std::move(recovery));
                const auto reset_status = installed_config::local_ignore_reset_status(*reset);
                if (static_cast<int>(reset_status.has_reset) + static_cast<int>(reset_status.has_conflict) +
                        static_cast<int>(reset_status.has_error) !=
                    1)
                    throw RunnerError("invalid reset result presence flags");
                if (reset_status.has_conflict) {
                    const auto conflict = installed_config::local_ignore_reset_take_conflict(std::move(reset));
                    const bool has_actual =
                        installed_config::local_ignore_reset_conflict_has_actual_identity(*conflict);
                    const auto actual = installed_config::local_ignore_reset_conflict_actual_identity(*conflict);
                    const bool has_backup = installed_config::local_ignore_reset_conflict_has_backup_path(*conflict);
                    const auto backup =
                        owned_string(installed_config::local_ignore_reset_conflict_backup_path(*conflict));
                    if (!has_backup && !backup.empty())
                        throw RunnerError("absent conflict backup did not use empty sentinel");
                    if (!has_actual && (!actual.sha256.empty() || actual.byte_len != 0))
                        throw RunnerError("absent conflict identity did not use empty sentinel");
                    result["outcome"] = "reset_conflict";
                    result["recovery"]["decision"] =
                        json{{"status", "conflict"},
                             {"expectedIdentity",
                              installed_identity(
                                  installed_config::local_ignore_reset_conflict_expected_identity(*conflict), path)},
                             {"actualIdentity", has_actual ? installed_identity(actual, path) : json(nullptr)},
                             {"backupPath", has_backup ? json(relative_path(root, fs::path(backup))) : json(nullptr)}};
                } else if (reset_status.has_reset) {
                    auto committed = installed_config::local_ignore_reset_take_result(std::move(reset));
                    const auto malformed =
                        installed_config::local_ignore_reset_result_malformed_local_ignore_identity(*committed);
                    backup_alias = relative_path(
                        root,
                        fs::path(owned_string(installed_config::local_ignore_reset_result_backup_path(*committed))));
                    // Preserve the public path relation while normalizing only the unpredictable suffix.
                    const auto stem = "installation/CLASSIC Backup/YAML Data/Local Ignore/CLASSIC Ignore.yaml." +
                                      owned_string(malformed.sha256) + ".";
                    if (!backup_alias->starts_with(stem) || !backup_alias->ends_with(".bak"))
                        throw RunnerError("reset backup escaped its content-addressed namespace");
                    const auto backup_name = "installation/CLASSIC Backup/YAML Data/Local Ignore/<backup>";
                    result["recovery"]["decision"] = json{
                        {"status", "reset"},
                        {"localIgnorePath",
                         relative_path(
                             root, fs::path(owned_string(
                                       installed_config::local_ignore_reset_result_local_ignore_path(*committed))))},
                        {"malformedIdentity", installed_identity(malformed, path)},
                        {"backupIdentity",
                         installed_identity(installed_config::local_ignore_reset_result_backup_identity(*committed),
                                            backup_name)},
                        {"replacementIdentity",
                         installed_identity(
                             installed_config::local_ignore_reset_result_replacement_identity(*committed), path)}};
                    const auto reset_diagnostics = installed_diagnostics(
                        installed_config::local_ignore_reset_result_diagnostics(*committed), root);
                    const auto snapshot =
                        installed_config::local_ignore_reset_result_take_snapshot(std::move(committed));
                    installed_snapshot(result, *snapshot, root);
                    if (result["diagnostics"] != reset_diagnostics)
                        throw RunnerError("reset snapshot lost retained diagnostics");
                    result["outcome"] = "reset";
                } else {
                    throw RunnerError("unexpected reset operational error");
                }
            }
        }
    } else {
        throw RunnerError("unsupported Installed YAML Data fixture operation");
    }
    result["files"] = installed_files(root);
    if (backup_alias) {
        for (auto& file : result["files"])
            if (file["path"] == *backup_alias)
                file["path"] = "installation/CLASSIC Backup/YAML Data/Local Ignore/<backup>";
        std::sort(result["files"].begin(), result["files"].end(),
                  [](const json& a, const json& b) { return a.at("path") < b.at("path"); });
    }
    return result;
}
