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

/// Forwards the pack's requested typed values without duplicating Rust validation or defaults.
classic::settings::UserSettingsUpdateDto settings_requested_update(const json& requested) {
    classic::settings::UserSettingsUpdateDto update{};
    for (const auto& [field, value] : requested.items()) {
        if (field == "/CLASSIC_Settings/Update Check") {
            update.has_update_check = true;
            update.update_check = value.get<bool>();
        } else if (field == "/CLASSIC_Settings/Max Concurrent Scans") {
            update.has_max_concurrent_scans = true;
            update.max_concurrent_scans = value.get<std::int64_t>();
        } else {
            throw RunnerError("unsupported requested User Settings field: " + field);
        }
    }
    return update;
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
        } else {
            throw RunnerError("unsupported observed User Settings field kind: " + kind);
        }
        fields.push_back(json{{"fieldPath", owned_string(field.field_path)}, {"value", std::move(value)}});
    }
    json diagnostics = json::array();
    for (const auto& diagnostic : preview.diagnostics) {
        diagnostics.push_back(
            json{{"fieldPath", diagnostic.has_field_path ? json(owned_string(diagnostic.field_path)) : json(nullptr)},
                 {"code", owned_string(diagnostic.code)},
                 {"message", owned_string(diagnostic.message)}});
    }
    return json{
        {"status", preview.accepted ? "accepted" : "rejected"},
        {"baseRevision", preview.base_revision.empty() ? json(nullptr) : json(owned_string(preview.base_revision))},
        {"acceptedFields", std::move(fields)},
        {"diagnostics", std::move(diagnostics)}};
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
    json commit{
        {"status", "not-attempted"}, {"revision", nullptr}, {"expectedRevision", nullptr}, {"actualRevision", nullptr}};
    if (input.at("commit").get<bool>() && preview.accepted) {
        const auto outcome =
            bootstrap ? classic::settings::user_settings_commit_bootstrap(root.string(), preview.base_revision, update)
                      : classic::settings::user_settings_commit_update(root.string(), preview.base_revision, update);
        const std::string status = owned_string(outcome.status);
        commit["status"] = status;
        if (status == "committed") {
            commit["revision"] = owned_string(outcome.revision);
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

/// Projects a public migration endpoint without interpreting its location or schema.
json settings_migration_endpoint(const rust::String& location, bool has_version, std::uint32_t major,
                                 std::uint32_t minor) {
    return json{{"location", owned_string(location)},
                {"schemaVersion", has_version ? json{{"major", major}, {"minor", minor}} : json(nullptr)}};
}

/// Retains every public review row and exact byte buffer for the central migration oracle.
json settings_migration_plan(const classic::settings::UserSettingsMigrationPlanningOutcomeDto& plan) {
    if (!plan.has_plan) {
        return nullptr;
    }
    if (!plan.has_original_content || !plan.has_proposed_content) {
        throw RunnerError("public migration plan omitted its retained content");
    }
    json changes = json::array();
    for (const auto& change : plan.changes) {
        changes.push_back(
            json{{"kind", owned_string(change.kind)},
                 {"sourcePath", change.has_source_path ? json(owned_string(change.source_path)) : json(nullptr)},
                 {"targetPath", change.has_target_path ? json(owned_string(change.target_path)) : json(nullptr)},
                 {"before", change.has_before ? json(owned_string(change.before)) : json(nullptr)},
                 {"after", change.has_after ? json(owned_string(change.after)) : json(nullptr)}});
    }
    return json{
        {"required", plan.required},
        {"baseRevision", owned_string(plan.base_revision)},
        {"source", settings_migration_endpoint(plan.source_location, plan.has_source_schema_version,
                                               plan.source_schema_major, plan.source_schema_minor)},
        {"target", settings_migration_endpoint(plan.target_location, plan.has_target_schema_version,
                                               plan.target_schema_major, plan.target_schema_minor)},
        {"changes", std::move(changes)},
        {"originalHex",
         settings_bytes_hex(std::vector<std::uint8_t>(plan.original_content.begin(), plan.original_content.end()))},
        {"proposedHex",
         settings_bytes_hex(std::vector<std::uint8_t>(plan.proposed_content.begin(), plan.proposed_content.end()))}};
}

/// Normalizes only the bridge status spelling and preserves ordered public diagnostic codes.
json settings_migration_planning(const classic::settings::UserSettingsMigrationPlanningOutcomeDto& outcome) {
    json diagnostics = json::array();
    for (const auto& diagnostic : outcome.diagnostics) {
        diagnostics.push_back(owned_string(diagnostic.code));
    }
    const std::string status = owned_string(outcome.status);
    return json{{"status", status == "not_required" ? "not-required" : status},
                {"diagnostics", std::move(diagnostics)},
                {"plan", settings_migration_plan(outcome)}};
}

/// Reads the public receipt projection while persistence authority stays in the opaque Rust handle.
json settings_migration_receipt(const fs::path& root,
                                const classic::settings::UserSettingsMigrationReceiptDto& receipt) {
    return json{{"sourcePath", path_carrier(root, fs::path(owned_string(receipt.source_path)))},
                {"destinationPath", path_carrier(root, fs::path(owned_string(receipt.destination_path)))},
                {"backupPath", path_carrier(root, fs::path(owned_string(receipt.backup_path)))},
                {"source", settings_migration_endpoint(receipt.source_location, receipt.has_source_schema_version,
                                                       receipt.source_schema_major, receipt.source_schema_minor)},
                {"target", settings_migration_endpoint(receipt.target_location, receipt.has_target_schema_version,
                                                       receipt.target_schema_major, receipt.target_schema_minor)},
                {"backupRevision", owned_string(receipt.backup_revision)},
                {"publishedRevision", owned_string(receipt.published_revision)}};
}

/// Extracts the stable core category from CXX's public error transport, rejecting unclassified failures.
std::string settings_migration_error_code(const rust::Error& error) {
    // CXX exposes Result failures as text; core Display prefixes its stable code before the first colon.
    const std::string message(error.what());
    const auto delimiter = message.find(':');
    const std::string code = message.substr(0, delimiter);
    if (delimiter == std::string::npos || !code.starts_with("migration_") ||
        !std::all_of(code.begin(), code.end(),
                     [](char value) { return (value >= 'a' && value <= 'z') || value == '_'; })) {
        throw RunnerError("public migration failure has no stable core code: " + message);
    }
    return code;
}

/// Applies one declared pre-operation fixture change, limiting backup mutations to the returned receipt path.
void settings_migration_interference(const json& plan, const json& scenario, const json& interference,
                                     const fs::path& root, const std::optional<fs::path>& backup_path = std::nullopt) {
    if (interference.is_null()) {
        return;
    }
    const std::string kind = interference.at("kind").get<std::string>();
    if (kind == "external-edit") {
        copy_fixture(plan, scenario, interference, root, "migration external edit");
    } else if (kind == "block-backup-directory" && !backup_path) {
        std::ofstream blocker(root / "CLASSIC Backup", std::ios::binary);
        blocker << "blocked";
        blocker.close();
        if (!blocker) {
            throw RunnerError("cannot create migration backup directory blocker");
        }
    } else if (kind == "tamper-backup" && backup_path) {
        const json placement{{"fixtureRef", interference.at("fixtureRef")},
                             {"path", relative_path(root, *backup_path)}};
        copy_fixture(plan, scenario, placement, root, "migration backup tamper");
    } else if (kind == "remove-backup" && backup_path) {
        if (!fs::remove(*backup_path)) {
            throw RunnerError("cannot remove returned migration backup");
        }
    } else {
        throw RunnerError("unsupported migration interference: " + kind);
    }
}

/// Observes pure planning, approved apply, and receipt-based restore through generated native CXX APIs.
json execute_user_settings_migration_scenario(const json& plan, const json& scenario) {
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),
                                 scenario.at("id").get<std::string>());
    const fs::path& root = temporary.path();
    const json& input = scenario.at("input");
    for (const auto& placement : input.at("installationData")) {
        copy_fixture(plan, scenario, placement, root, "installationData");
    }
    const auto planned = classic::settings::user_settings_plan_migration(root.string());
    const auto repeated = classic::settings::user_settings_plan_migration(root.string());
    json reversed = nullptr;
    json round_trip = nullptr;
    if (planned.has_plan) {
        const auto reverse = classic::settings::user_settings_reverse_migration_plan(planned);
        reversed = settings_migration_plan(reverse);
        round_trip = settings_migration_plan(classic::settings::user_settings_reverse_migration_plan(reverse));
    }
    const json after_planning = settings_operation_tree(root);
    json applied{{"status", "not-attempted"},
                 {"expectedRevision", nullptr},
                 {"actualRevision", nullptr},
                 {"errorCode", nullptr},
                 {"receipt", nullptr}};
    json restored{{"status", "not-attempted"},
                  {"revision", nullptr},
                  {"expectedRevision", nullptr},
                  {"actualRevision", nullptr},
                  {"errorCode", nullptr}};
    // Keep the real apply handle alive across observation and interference; receipt DTOs cannot authorize restore.
    std::optional<rust::Box<classic::settings::UserSettingsMigrationApplyHandle>> handle;
    std::optional<fs::path> backup_path;
    if (input.at("apply").get<bool>() && planned.has_plan) {
        settings_migration_interference(plan, scenario, input.at("beforeApply"), root);
        try {
            handle.emplace(classic::settings::user_settings_apply_migration(root.string(), planned));
            const auto outcome = classic::settings::user_settings_migration_apply_outcome(**handle);
            const std::string status = owned_string(outcome.status);
            applied["status"] = status;
            if (status == "applied" && outcome.has_receipt) {
                applied["receipt"] = settings_migration_receipt(root, outcome.receipt);
                backup_path = fs::path(owned_string(outcome.receipt.backup_path));
            } else if (status == "conflict" && !outcome.has_receipt) {
                applied["expectedRevision"] = owned_string(outcome.expected_revision);
                applied["actualRevision"] = owned_string(outcome.actual_revision);
            } else {
                throw RunnerError("unexpected public migration apply outcome: " + status);
            }
        } catch (const rust::Error& error) {
            applied["status"] = "error";
            applied["errorCode"] = settings_migration_error_code(error);
        }
    }
    const json after_apply = settings_operation_tree(root);
    if (input.at("restore").get<bool>() && backup_path) {
        settings_migration_interference(plan, scenario, input.at("beforeRestore"), root, backup_path);
        try {
            const auto outcome = classic::settings::user_settings_restore_migration(root.string(), **handle);
            const std::string status = owned_string(outcome.status);
            restored["status"] = status;
            if (status == "restored") {
                restored["revision"] = owned_string(outcome.revision);
            } else if (status == "conflict") {
                restored["expectedRevision"] = owned_string(outcome.expected_revision);
                restored["actualRevision"] = owned_string(outcome.actual_revision);
            } else {
                throw RunnerError("unexpected public migration restore outcome: " + status);
            }
        } catch (const rust::Error& error) {
            restored["status"] = "error";
            restored["errorCode"] = settings_migration_error_code(error);
        }
    }
    return json{{"planning", settings_migration_planning(planned)},
                {"repeatedPlanning", settings_migration_planning(repeated)},
                {"reversedPlan", std::move(reversed)},
                {"roundTripPlan", std::move(round_trip)},
                {"afterPlanningTree", after_planning},
                {"apply", std::move(applied)},
                {"afterApplyTree", after_apply},
                {"restore", std::move(restored)},
                {"finalTree", settings_operation_tree(root)}};
}

/// Dispatches input-only User Settings scenarios to their public API observations.
json execute_user_settings_scenario(const json& plan, const json& scenario) {
    if (scenario.at("action") == "user-settings.migrate") {
        return execute_user_settings_migration_scenario(plan, scenario);
    }
    return scenario.at("action") == "user-settings.open" ? execute_user_settings_open_scenario(plan, scenario)
                                                         : execute_user_settings_operation_scenario(plan, scenario);
}
