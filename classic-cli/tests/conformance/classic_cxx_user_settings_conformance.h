// SPDX-License-Identifier: MIT
// Private User Settings observations share the enclosing runner's receipt,
// fixture materialization, path, and digest utilities. No frontend is linked.

#include "classic_cxx_user_settings_defaults_conformance.h"

/// Reads exact source bytes so public revision and retained content can be checked independently.
std::vector<std::uint8_t> settings_source_bytes(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw RunnerError("cannot read observed User Settings source: " + path.string());
    }
    const std::vector<std::uint8_t> bytes{std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
    if (input.bad()) {
        throw RunnerError("cannot finish reading observed User Settings source: " + path.string());
    }
    return bytes;
}

/// Captures directories and exact file identities, including empty directories created by an open.
json settings_tree_snapshot(const fs::path& root) {
    json tree = json::object();
    for (const auto& entry : fs::recursive_directory_iterator(root)) {
        const std::string path = relative_path(root, entry.path());
        if (entry.is_directory()) {
            tree[path] = json{{"kind", "directory"}};
        } else if (entry.is_regular_file()) {
            tree[path] = json{{"kind", "file"}, {"sha256", Sha256::digest(settings_source_bytes(entry.path()))}};
        } else {
            throw RunnerError("unexpected non-regular User Settings tree entry: " + path);
        }
    }
    return tree;
}

/// Projects only centrally requested public typed fields, rejecting unknown input selectors.
json settings_selected_view(const classic::settings::GuiSettingsSnapshotDto& snapshot, const json& fields) {
    const auto& update = snapshot.update_preferences;
    const auto& scan = snapshot.crash_log_scan;
    const auto& setup = snapshot.game_setup;
    const auto& frontend = snapshot.frontend_state;
    json view = json::object();
    for (const auto& selector : fields) {
        const std::string field = selector.get<std::string>();
        if (field == "update_check") {
            view[field] = update.update_check_enabled;
        } else if (field == "game_version") {
            view[field] = owned_string(scan.game_version_selection);
        } else if (field == "move_unsolved_logs") {
            view[field] = scan.move_unsolved_logs;
        } else if (field == "max_concurrent_scans") {
            view[field] = scan.max_concurrent_scans;
        } else if (field == "fcx_mode") {
            view[field] = scan.fcx_mode;
        } else if (field == "simplify_logs") {
            view[field] = scan.simplify_logs;
        } else if (field == "show_formid_values") {
            view[field] = scan.formid_value_lookup;
        } else if (field == "custom_scan_folder") {
            view[field] = scan.has_custom_scan_input ? json(owned_string(scan.custom_scan_input)) : json(nullptr);
        } else if (field == "mods_folder") {
            view[field] = setup.has_mods_root ? json(owned_string(setup.mods_root)) : json(nullptr);
        } else if (field == "formid_databases") {
            json databases = json::object();
            for (const auto& game : scan.formid_database_games) {
                databases[owned_string(game)] = json::array();
            }
            for (const auto& row : scan.formid_database_paths) {
                databases.at(owned_string(row.game)).push_back(owned_string(row.path));
            }
            view[field] = std::move(databases);
        } else if (field == "scan_formid_databases") {
            // Rust publishes only games whose scan reads at least one row, already in read order.
            json databases = json::object();
            for (const auto& row : scan.scan_formid_database_paths) {
                const std::string game = owned_string(row.game);
                if (!databases.contains(game)) {
                    databases[game] = json::array();
                }
                databases.at(game).push_back(owned_string(row.path));
            }
            view[field] = std::move(databases);
        } else {
            bool recognized = false;
            for (const auto& geometry : frontend.window_geometry) {
                const std::string tab = owned_string(geometry.tab);
                if (field == tab) {
                    view[field] =
                        json{{"maximized", geometry.maximized}, {"width", geometry.width}, {"height", geometry.height}};
                    recognized = true;
                } else if (tab == "main_tab" && field == "main_tab_width") {
                    view[field] = geometry.width;
                    recognized = true;
                } else if (tab == "main_tab" && field == "main_tab_maximized") {
                    view[field] = geometry.maximized;
                    recognized = true;
                }
            }
            if (!recognized) {
                throw RunnerError("unsupported User Settings observation field: " + field);
            }
        }
    }
    return view;
}

/// Opens a fresh isolated fixture through the public bridge and observes read-only behavior.
json execute_user_settings_open_scenario(const json& plan, const json& scenario) {
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),
                                 scenario.at("id").get<std::string>());
    const json& input = scenario.at("input");
    for (const auto& placement : input.at("installationData")) {
        copy_fixture(plan, scenario, placement, temporary.path(), "installationData");
    }
    const json before = settings_tree_snapshot(temporary.path());
    // The aggregate is a public bridge DTO projected from one Rust open, so
    // every selected typed group describes the same retained source revision.
    auto snapshot = classic::settings::user_settings_open_gui_settings(temporary.path().string());
    // Exercise the standalone Game Setup entry point; selected fields below observe its result.
    snapshot.game_setup = classic::settings::user_settings_open_game_setup_settings(temporary.path().string());
    const auto& update = snapshot.update_preferences;
    const std::string source_path = owned_string(update.source_path);
    const bool has_source = !source_path.empty();
    const auto source_bytes = has_source ? settings_source_bytes(fs::path(source_path)) : std::vector<std::uint8_t>{};
    const std::string revision = owned_string(update.revision);
    const std::string revision_kind = revision.starts_with("sha256:") ? "sha256" : revision;
    const bool revision_matches =
        has_source ? revision == "sha256:" + Sha256::digest(source_bytes) : revision == "missing";
    const bool content_matches = update.has_original_content == has_source &&
                                 (!has_source || (update.original_content.size() == source_bytes.size() &&
                                                  std::equal(update.original_content.begin(),
                                                             update.original_content.end(), source_bytes.begin())));
    json diagnostics = json::array();
    for (const auto& diagnostic : update.diagnostics) {
        diagnostics.push_back(owned_string(diagnostic.code));
    }
    return json{
        {"source", json{{"location", owned_string(update.source_location)},
                        {"path", has_source ? path_carrier(temporary.path(), fs::path(source_path)) : json(nullptr)},
                        {"classification", owned_string(update.classification)}}},
        {"commitEligibility", owned_string(update.commit_eligibility)},
        {"diagnostics", std::move(diagnostics)},
        {"view", settings_selected_view(snapshot, input.at("observationFields"))},
        {"durableEffects", json{{"treeUnchanged", before == settings_tree_snapshot(temporary.path())}}},
        {"revision", json{{"kind", revision_kind}, {"matchesSourceBytes", revision_matches}}},
        {"originalContent", json{{"present", update.has_original_content}, {"matchesSourceBytes", content_matches}}}};
}

/// Encodes exact file bytes without interpreting settings content in the participant.
std::string settings_bytes_hex(const std::vector<std::uint8_t>& bytes) {
    constexpr std::string_view digits = "0123456789abcdef";
    std::string encoded;
    encoded.reserve(bytes.size() * 2);
    for (const auto byte : bytes) {
        encoded.push_back(digits[byte >> 4]);
        encoded.push_back(digits[byte & 0x0f]);
    }
    return encoded;
}

/// Observes the complete installation tree, retaining empty directories and lock files.
json settings_operation_tree(const fs::path& root) {
    json tree = json::array();
    const auto root_status = fs::symlink_status(root);
    if (root_status.type() == fs::file_type::not_found) {
        return tree;
    }
    if (!fs::is_directory(root_status)) {
        throw RunnerError("User Settings installation root is not a regular directory");
    }
    tree.push_back(json{{"path", path_carrier(root, root)}, {"kind", "directory"}});
    std::vector<fs::path> paths;
    for (const auto& entry : fs::recursive_directory_iterator(root)) {
        paths.push_back(entry.path());
    }
    std::sort(paths.begin(), paths.end(), [&root](const auto& left, const auto& right) {
        return relative_path(root, left) < relative_path(root, right);
    });
    for (const auto& path : paths) {
        // Inspect the entry itself so links cannot masquerade as ordinary durable files.
        const auto status = fs::symlink_status(path);
        if (fs::is_directory(status)) {
            tree.push_back(json{{"path", path_carrier(root, path)}, {"kind", "directory"}});
        } else if (fs::is_regular_file(status)) {
            tree.push_back(json{{"path", path_carrier(root, path)},
                                {"kind", "file"},
                                {"bytesHex", settings_bytes_hex(settings_source_bytes(path))}});
        } else {
            throw RunnerError("unexpected non-regular User Settings tree entry: " + relative_path(root, path));
        }
    }
    return tree;
}

/// Request selector prefix naming a game-aware FormID database save for the trailing game.
const std::string kFormIdDatabaseSavePrefix = "/CLASSIC_Settings/FormID Databases/";

/// Forwards the pack's requested typed values without duplicating Rust validation or defaults.
classic::settings::UserSettingsUpdateDto settings_requested_update(const json& requested) {
    classic::settings::UserSettingsUpdateDto update{};
    if (requested.contains("/UI/window_geometry/main_tab/maximized")) {
        classic::settings::UserSettingsWindowGeometryUpdateDto geometry{};
        geometry.tab = "main_tab";
        geometry.maximized = requested.at("/UI/window_geometry/main_tab/maximized").get<bool>();
        geometry.width = requested.at("/UI/window_geometry/main_tab/width").get<std::int64_t>();
        geometry.height = requested.at("/UI/window_geometry/main_tab/height").get<std::int64_t>();
        update.window_geometry_updates.push_back(std::move(geometry));
    }
    if (requested.contains("/UI/tui/active_tab")) {
        update.has_tui_remembered_state = true;
        update.tui_active_tab = requested.at("/UI/tui/active_tab").get<std::int64_t>();
        update.tui_results_panel_width = requested.at("/UI/tui/results_panel_width").get<std::int64_t>();
        update.tui_sort_ascending = requested.at("/UI/tui/sort_ascending").get<bool>();
    }
    for (const auto& [field, value] : requested.items()) {
        if (field == "/UI/window_geometry/main_tab/maximized" || field == "/UI/window_geometry/main_tab/width" ||
            field == "/UI/window_geometry/main_tab/height" || field == "/UI/tui/active_tab" ||
            field == "/UI/tui/results_panel_width" || field == "/UI/tui/sort_ascending")
            continue;
        if (field == "/CLASSIC_Settings/Update Check") {
            update.has_update_check = true;
            update.update_check = value.get<bool>();
        } else if (field == "/CLASSIC_Settings/Update Source") {
            update.has_update_source = true;
            update.update_source = value.get<std::string>();
        } else if (field == "/UI/preferences/auto_switch_after_scan") {
            update.has_auto_switch_after_scan = true;
            update.auto_switch_after_scan = value.get<bool>();
        } else if (field == "/CLASSIC_Settings/Managed Game") {
            update.has_managed_game = true;
            update.managed_game = value.get<std::string>();
        } else if (field == "/CLASSIC_Settings/Game Version") {
            update.has_game_version_selection = true;
            update.game_version_selection = value.get<std::string>();
        } else if (field == "/CLASSIC_Settings/Game Folder Path") {
            update.has_game_root = true;
            update.has_game_root_value = !value.is_null();
            if (!value.is_null())
                update.game_root = value.get<std::string>();
        } else if (field == "/CLASSIC_Settings/Game EXE Path") {
            update.has_game_executable = true;
            update.has_game_executable_value = !value.is_null();
            if (!value.is_null())
                update.game_executable = value.get<std::string>();
        } else if (field == "/CLASSIC_Settings/Documents Folder Path") {
            update.has_documents_root = true;
            update.has_documents_root_value = !value.is_null();
            if (!value.is_null())
                update.documents_root = value.get<std::string>();
        } else if (field == "/CLASSIC_Settings/INI Folder Path") {
            update.has_ini_folder = true;
            update.has_ini_folder_value = !value.is_null();
            if (!value.is_null())
                update.ini_folder = value.get<std::string>();
        } else if (field == "/CLASSIC_Settings/MODS Folder Path") {
            update.has_mods_folder = true;
            update.has_mods_folder_value = !value.is_null();
            if (!value.is_null())
                update.mods_folder = value.get<std::string>();
        } else if (field == "/CLASSIC_Settings/FCX Mode") {
            update.has_fcx_mode = true;
            update.fcx_mode = value.get<bool>();
        } else if (field == "/CLASSIC_Settings/Simplify Logs") {
            update.has_simplify_logs = true;
            update.simplify_logs = value.get<bool>();
        } else if (field == "/CLASSIC_Settings/Show Statistics") {
            update.has_show_statistics = true;
            update.show_statistics = value.get<bool>();
        } else if (field == "/CLASSIC_Settings/Show FormID Values") {
            update.has_formid_value_lookup = true;
            update.formid_value_lookup = value.get<bool>();
        } else if (field == "/CLASSIC_Settings/FormID Databases") {
            update.has_formid_databases = true;
            for (const auto& [game, paths] : value.items()) {
                update.formid_database_games.push_back(game);
                for (const auto& path : paths) {
                    classic::settings::FormIdDatabasePathDto row{};
                    row.game = game;
                    row.path = path.get<std::string>();
                    update.formid_database_paths.push_back(std::move(row));
                }
            }
        } else if (field.rfind(kFormIdDatabaseSavePrefix, 0) == 0 &&
                   field.size() > kFormIdDatabaseSavePrefix.size()) {
            // A pointer below the mapping names one game's game-aware save, not a raw key write.
            update.has_formid_database_save = true;
            update.formid_database_save_game = field.substr(kFormIdDatabaseSavePrefix.size());
            for (const auto& path : value) {
                update.formid_database_save_paths.push_back(path.get<std::string>());
            }
        } else if (field == "/CLASSIC_Settings/Move Unsolved Logs") {
            update.has_move_unsolved_logs = true;
            update.move_unsolved_logs = value.get<bool>();
        } else if (field == "/CLASSIC_Settings/Unsolved Logs Destination") {
            update.has_unsolved_logs_destination = true;
            update.has_unsolved_logs_destination_value = !value.is_null();
            if (!value.is_null())
                update.unsolved_logs_destination = value.get<std::string>();
        } else if (field == "/CLASSIC_Settings/SCAN Custom Path") {
            update.has_custom_scan_input = true;
            update.has_custom_scan_input_value = !value.is_null();
            if (!value.is_null())
                update.custom_scan_input = value.get<std::string>();
        } else if (field == "/CLASSIC_Settings/Papyrus Log Path") {
            update.has_papyrus_log_path = true;
            update.has_papyrus_log_path_value = !value.is_null();
            if (!value.is_null())
                update.papyrus_log_path = value.get<std::string>();
        } else if (field == "/CLASSIC_Settings/Max Concurrent Scans") {
            update.has_max_concurrent_scans = true;
            update.max_concurrent_scans = value.get<std::int64_t>();
        } else
            throw RunnerError("unsupported requested User Settings field: " + field);
    }
    return update;
}

/// Projects ordered update diagnostics, rejecting or not, into the shared observation shape.
json settings_update_diagnostics(const rust::Vec<classic::settings::UserSettingsUpdateDiagnosticDto>& source) {
    json diagnostics = json::array();
    for (const auto& diagnostic : source) {
        diagnostics.push_back(
            json{{"fieldPath", diagnostic.has_field_path ? json(owned_string(diagnostic.field_path)) : json(nullptr)},
                 {"code", owned_string(diagnostic.code)},
                 {"message", owned_string(diagnostic.message)}});
    }
    return diagnostics;
}

/// Projects values and ordered diagnostics from the returned public preview artifact.
json settings_operation_preview(const classic::settings::UserSettingsUpdatePreviewDto& preview) {
    json fields = json::array();
    for (const auto& field : preview.accepted_fields) {
        const std::string kind = owned_string(field.value_kind);
        json value;
        if (kind == "bool") {
            value = field.bool_value;
        } else if (kind == "u32") {
            value = field.u32_value;
        } else if (kind == "string" || kind == "optional_string") {
            value = field.has_string_value ? json(owned_string(field.string_value)) : json(nullptr);
        } else if (kind == "formid_databases") {
            value = json::object();
            for (const auto& game : preview.formid_database_games)
                value[owned_string(game)] = json::array();
            for (const auto& row : preview.formid_database_paths)
                value[owned_string(row.game)].push_back(owned_string(row.path));
        } else {
            throw RunnerError("unsupported observed User Settings field kind: " + kind);
        }
        fields.push_back(json{{"fieldPath", owned_string(field.field_path)}, {"value", std::move(value)}});
    }
    return json{
        {"status", preview.accepted ? "accepted" : "rejected"},
        {"baseRevision", preview.base_revision.empty() ? json(nullptr) : json(owned_string(preview.base_revision))},
        {"acceptedFields", std::move(fields)},
        {"diagnostics", settings_update_diagnostics(preview.diagnostics)}};
}

/// Previews and optionally commits an isolated operation through the public Rust bridge.
json execute_user_settings_operation_scenario(const json& plan, const json& scenario) {
    const std::string action = scenario.at("action").get<std::string>();
    if (action != "user-settings.update") {
        throw RunnerError("unsupported User Settings conformance action: " + action);
    }
    const json& input = scenario.at("input");
    const std::string mode = input.at("previewMode").get<std::string>();
    const bool bootstrap = mode == "bootstrap";
    if (!bootstrap && mode != "update") {
        throw RunnerError("unsupported User Settings preview mode: " + mode);
    }
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),
                                 scenario.at("id").get<std::string>());
    // Missing-root scenarios must not acquire a root through harness setup;
    // first-run commit scenarios explicitly provide the installation directory.
    const fs::path root = temporary.path() / "installation";
    if (input.at("installationRootExists").get<bool>()) {
        fs::create_directory(root);
    }
    for (const auto& placement : input.at("installationData")) {
        copy_fixture(plan, scenario, placement, root, "installationData");
    }
    const auto update = settings_requested_update(input.at("requestedUpdate"));
    const auto preview = bootstrap ? classic::settings::user_settings_preview_bootstrap(root.string(), update)
                                   : classic::settings::user_settings_preview_update(root.string(), update);
    const json after_preview = settings_operation_tree(root);
    const json& external_edit = input.at("externalEdit");
    if (!external_edit.is_null()) {
        copy_fixture(plan, scenario, external_edit, root, "externalEdit");
    }
    json commit{{"status", "not-attempted"},
                {"revision", nullptr},
                {"expectedRevision", nullptr},
                {"actualRevision", nullptr},
                {"diagnostics", json::array()}};
    if (input.at("commit").get<bool>() && preview.accepted) {
        const auto outcome =
            bootstrap ? classic::settings::user_settings_commit_bootstrap(root.string(), preview.base_revision, update)
                      : classic::settings::user_settings_commit_update(root.string(), preview.base_revision, update);
        const std::string status = owned_string(outcome.status);
        commit["status"] = status;
        if (status == "committed") {
            commit["revision"] = owned_string(outcome.revision);
            commit["diagnostics"] = settings_update_diagnostics(outcome.diagnostics);
        } else if (status == "conflict") {
            commit["expectedRevision"] = owned_string(outcome.expected_revision);
            commit["actualRevision"] = owned_string(outcome.actual_revision);
        } else {
            throw RunnerError("unexpected User Settings commit status after accepted preview: " + status);
        }
    }
    return json{{"preview", settings_operation_preview(preview)},
                {"afterPreviewTree", after_preview},
                {"commit", std::move(commit)},
                {"finalTree", settings_operation_tree(root)}};
}

/// Commit a native geometry transition and verify the returned revision against final bytes.
json execute_user_settings_geometry(const json& plan, const json& scenario) {
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),
                                 scenario.at("id").get<std::string>());
    const auto& root = temporary.path();
    for (const auto& item : scenario.at("input").at("installationData"))
        copy_fixture(plan, scenario, item, root, "installationData");
    const auto initial = classic::settings::user_settings_open_gui_settings(root.string());
    if (scenario.at("input").at("blockLock").get<bool>())
        fs::create_directory(root / "CLASSIC Settings.yaml.commit.lock");
    classic::settings::UserSettingsWindowGeometryUpdateDto update{};
    update.tab = "main_tab";
    update.width = 900;
    update.height = 650;
    update.maximized = false;
    json transition;
    try {
        const auto outcome = classic::settings::user_settings_commit_frontend_geometry_transition(
            root.string(), initial.update_preferences.revision, update);
        if (owned_string(outcome.status) != "committed")
            throw RunnerError("unexpected geometry outcome");
        transition = json{
            {"status", "committed"},
            {"code", nullptr},
            {"hasMessage", nullptr},
            {"revisionMatches", owned_string(outcome.revision) ==
                                    "sha256:" + Sha256::digest(settings_source_bytes(root / "CLASSIC Settings.yaml"))}};
    } catch (const rust::Error& error) {
        const std::string message = error.what();
        const auto split = message.find(": ");
        if (split == std::string::npos)
            throw RunnerError("geometry error has no stable code prefix");
        transition = json{{"status", "error"},
                          {"code", message.substr(0, split)},
                          {"hasMessage", message.size() > split + 2},
                          {"revisionMatches", nullptr}};
    }
    const auto current = classic::settings::user_settings_open_gui_settings(root.string());
    const auto geometry = settings_selected_view(current, json::array({"main_tab"})).at("main_tab");
    const auto final_tree = settings_tree_snapshot(root);
    json files = json::array();
    for (const auto& [path, item] : final_tree.items())
        files.push_back(json{{"path", path}, {"kind", item.at("kind")}});
    return json{{"transition", transition}, {"geometry", geometry}, {"files", files}};
}

/// Dispatches input-only User Settings scenarios to their public API observations.
///
/// `user-settings.legacy-import` and `user-settings.migrate` left CXX with the
/// legacy-import and reverse-plan exports their observations need (#309).
json execute_user_settings_scenario(const json& plan, const json& scenario) {
    if (scenario.at("action") == "user-settings.geometry")
        return execute_user_settings_geometry(plan, scenario);
    if (scenario.at("action") == "user-settings.defaults") {
        return settings_defaults_projection();
    }
    return scenario.at("action") == "user-settings.open" ? execute_user_settings_open_scenario(plan, scenario)
                                                         : execute_user_settings_operation_scenario(plan, scenario);
}
