// SPDX-License-Identifier: MIT
/// Observe every typed public default including per-field origin metadata.
json settings_defaults_projection() {
    const auto snapshot = classic::settings::user_settings_gui_published_defaults();
    json projection = json::object();
    projection["update.update_check"] = snapshot.update_preferences.update_check_enabled;
    projection["update.update_check_origin"] = owned_string(snapshot.update_preferences.update_check_origin);
    projection["update.update_source"] = owned_string(snapshot.update_preferences.update_source);
    projection["update.update_source_origin"] = owned_string(snapshot.update_preferences.update_source_origin);
    projection["scan.fcx_mode"] = snapshot.crash_log_scan.fcx_mode;
    projection["scan.fcx_mode_origin"] = owned_string(snapshot.crash_log_scan.fcx_mode_origin);
    projection["scan.simplify_logs"] = snapshot.crash_log_scan.simplify_logs;
    projection["scan.simplify_logs_origin"] = owned_string(snapshot.crash_log_scan.simplify_logs_origin);
    projection["scan.show_statistics"] = snapshot.crash_log_scan.show_statistics;
    projection["scan.show_statistics_origin"] = owned_string(snapshot.crash_log_scan.show_statistics_origin);
    projection["scan.formid_value_lookup"] = snapshot.crash_log_scan.formid_value_lookup;
    projection["scan.formid_value_lookup_origin"] = owned_string(snapshot.crash_log_scan.formid_value_lookup_origin);
    json databases = json::object();
    for (const auto& game : snapshot.crash_log_scan.formid_database_games)
        databases[owned_string(game)] = json::array();
    for (const auto& row : snapshot.crash_log_scan.formid_database_paths)
        databases[owned_string(row.game)].push_back(owned_string(row.path));
    projection["scan.formid_databases"] = databases;
    projection["scan.formid_databases_origin"] = owned_string(snapshot.crash_log_scan.formid_databases_origin);
    projection["scan.move_unsolved_logs"] = snapshot.crash_log_scan.move_unsolved_logs;
    projection["scan.move_unsolved_logs_origin"] = owned_string(snapshot.crash_log_scan.move_unsolved_logs_origin);
    projection["scan.unsolved_logs_destination"] =
        (snapshot.crash_log_scan.has_unsolved_logs_destination
             ? json(owned_string(snapshot.crash_log_scan.unsolved_logs_destination))
             : json(nullptr));
    projection["scan.unsolved_logs_destination_origin"] =
        owned_string(snapshot.crash_log_scan.unsolved_logs_destination_origin);
    projection["scan.custom_scan_input"] =
        (snapshot.crash_log_scan.has_custom_scan_input ? json(owned_string(snapshot.crash_log_scan.custom_scan_input))
                                                       : json(nullptr));
    projection["scan.custom_scan_input_origin"] = owned_string(snapshot.crash_log_scan.custom_scan_input_origin);
    projection["scan.game_version_selection"] = owned_string(snapshot.crash_log_scan.game_version_selection);
    projection["scan.game_version_selection_origin"] =
        owned_string(snapshot.crash_log_scan.game_version_selection_origin);
    projection["scan.max_concurrent_scans"] = snapshot.crash_log_scan.max_concurrent_scans;
    projection["scan.max_concurrent_scans_origin"] = owned_string(snapshot.crash_log_scan.max_concurrent_scans_origin);
    projection["setup.managed_game"] = owned_string(snapshot.game_setup.managed_game);
    projection["setup.managed_game_origin"] = owned_string(snapshot.game_setup.managed_game_origin);
    projection["setup.game_version_selection"] = owned_string(snapshot.game_setup.game_version_selection);
    projection["setup.game_version_selection_origin"] = owned_string(snapshot.game_setup.game_version_selection_origin);
    projection["setup.game_root"] =
        (snapshot.game_setup.has_game_root ? json(owned_string(snapshot.game_setup.game_root)) : json(nullptr));
    projection["setup.game_root_origin"] = owned_string(snapshot.game_setup.game_root_origin);
    projection["setup.game_executable"] =
        (snapshot.game_setup.has_game_executable ? json(owned_string(snapshot.game_setup.game_executable))
                                                 : json(nullptr));
    projection["setup.game_executable_origin"] = owned_string(snapshot.game_setup.game_executable_origin);
    projection["setup.documents_root"] =
        (snapshot.game_setup.has_documents_root ? json(owned_string(snapshot.game_setup.documents_root))
                                                : json(nullptr));
    projection["setup.documents_root_origin"] = owned_string(snapshot.game_setup.documents_root_origin);
    projection["setup.ini_folder"] =
        (snapshot.game_setup.has_ini_folder ? json(owned_string(snapshot.game_setup.ini_folder)) : json(nullptr));
    projection["setup.ini_folder_origin"] = owned_string(snapshot.game_setup.ini_folder_origin);
    projection["setup.mods_root"] =
        (snapshot.game_setup.has_mods_root ? json(owned_string(snapshot.game_setup.mods_root)) : json(nullptr));
    projection["setup.mods_root_origin"] = owned_string(snapshot.game_setup.mods_root_origin);
    projection["setup.custom_scan_input"] =
        (snapshot.game_setup.has_custom_scan_input ? json(owned_string(snapshot.game_setup.custom_scan_input))
                                                   : json(nullptr));
    projection["setup.custom_scan_input_origin"] = owned_string(snapshot.game_setup.custom_scan_input_origin);
    projection["setup.papyrus_log"] =
        (snapshot.game_setup.has_papyrus_log ? json(owned_string(snapshot.game_setup.papyrus_log)) : json(nullptr));
    projection["setup.papyrus_log_origin"] = owned_string(snapshot.game_setup.papyrus_log_origin);
    projection["preferences.auto_switch_after_scan"] = snapshot.frontend_state.auto_switch_after_scan;
    projection["preferences.auto_switch_after_scan_origin"] =
        owned_string(snapshot.frontend_state.auto_switch_after_scan_origin);
    projection["preferences.auto_refresh_interval_ms"] = snapshot.frontend_state.auto_refresh_interval_ms;
    projection["preferences.auto_refresh_interval_ms_origin"] =
        owned_string(snapshot.frontend_state.auto_refresh_interval_ms_origin);
    projection["tui.active_tab"] = snapshot.frontend_state.tui_active_tab;
    projection["tui.active_tab_origin"] = owned_string(snapshot.frontend_state.tui_active_tab_origin);
    projection["tui.results_panel_width"] = snapshot.frontend_state.tui_results_panel_width;
    projection["tui.results_panel_width_origin"] = owned_string(snapshot.frontend_state.tui_results_panel_width_origin);
    projection["tui.sort_ascending"] = snapshot.frontend_state.tui_sort_ascending;
    projection["tui.sort_ascending_origin"] = owned_string(snapshot.frontend_state.tui_sort_ascending_origin);
    for (const auto& geometry : snapshot.frontend_state.window_geometry) {
        projection[owned_string(geometry.tab) + ".maximized"] = geometry.maximized;
        projection[owned_string(geometry.tab) + ".width"] = geometry.width;
        projection[owned_string(geometry.tab) + ".height"] = geometry.height;
        projection[owned_string(geometry.tab) + ".maximized_origin"] = owned_string(geometry.maximized_origin);
        projection[owned_string(geometry.tab) + ".width_origin"] = owned_string(geometry.width_origin);
        projection[owned_string(geometry.tab) + ".height_origin"] = owned_string(geometry.height_origin);
    }
    return json{{"projection", projection}};
}
