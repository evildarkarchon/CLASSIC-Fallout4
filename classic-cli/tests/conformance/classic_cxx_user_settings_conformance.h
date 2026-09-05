// SPDX-License-Identifier: MIT
// Private User Settings observations share the enclosing runner's receipt,
// fixture materialization, path, and digest utilities. No frontend is linked.

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
json execute_user_settings_scenario(const json& plan, const json& scenario) {
    if (scenario.at("action") != "user-settings.open") {
        throw RunnerError("unsupported User Settings conformance action");
    }
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),
                                 scenario.at("id").get<std::string>());
    const json& input = scenario.at("input");
    for (const auto& placement : input.at("installationData")) {
        copy_fixture(plan, scenario, placement, temporary.path(), "installationData");
    }
    const json before = settings_tree_snapshot(temporary.path());
    // The aggregate is a public bridge DTO projected from one Rust open, so
    // every selected typed group describes the same retained source revision.
    const auto snapshot = classic::settings::user_settings_open_gui_settings(temporary.path().string());
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
