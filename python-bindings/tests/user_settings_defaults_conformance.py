"""Read every public typed default without accessing an installation."""


def observe_defaults() -> dict:
    """Project real Python getters into the common full-defaults receipt."""
    import classic_user_settings

    snapshot = classic_user_settings.user_settings_published_defaults()
    groups = {
        "update": snapshot.update_preferences,
        "scan": snapshot.crash_log_scan_settings,
        "setup": snapshot.game_setup_settings,
        "preferences": snapshot.frontend_state.preferences,
        "tui": snapshot.frontend_state.tui,
    }
    for tab in ("main_tab", "backups_tab", "articles_tab", "results_tab"):
        groups[tab] = getattr(snapshot.frontend_state.window_geometry, tab)
    projection = {}
    projection["update.update_check"] = groups["update"].update_check
    projection["update.update_check_origin"] = groups["update"].origin
    projection["update.update_source"] = groups["update"].update_source
    projection["update.update_source_origin"] = groups["update"].update_source_origin
    projection["scan.fcx_mode"] = groups["scan"].fcx_mode
    projection["scan.fcx_mode_origin"] = groups["scan"].fcx_mode_origin
    projection["scan.simplify_logs"] = groups["scan"].simplify_logs
    projection["scan.simplify_logs_origin"] = groups["scan"].simplify_logs_origin
    projection["scan.show_statistics"] = groups["scan"].show_statistics
    projection["scan.show_statistics_origin"] = groups["scan"].show_statistics_origin
    projection["scan.formid_value_lookup"] = groups["scan"].formid_value_lookup
    projection["scan.formid_value_lookup_origin"] = groups[
        "scan"
    ].formid_value_lookup_origin
    projection["scan.formid_databases"] = groups["scan"].formid_databases
    projection["scan.formid_databases_origin"] = groups["scan"].formid_databases_origin
    projection["scan.move_unsolved_logs"] = groups["scan"].move_unsolved_logs
    projection["scan.move_unsolved_logs_origin"] = groups[
        "scan"
    ].move_unsolved_logs_origin
    projection["scan.unsolved_logs_destination"] = groups[
        "scan"
    ].unsolved_logs_destination
    projection["scan.unsolved_logs_destination_origin"] = groups[
        "scan"
    ].unsolved_logs_destination_origin
    projection["scan.custom_scan_input"] = groups["scan"].custom_scan_input
    projection["scan.custom_scan_input_origin"] = groups[
        "scan"
    ].custom_scan_input_origin
    projection["scan.game_version_selection"] = groups["scan"].game_version_selection
    projection["scan.game_version_selection_origin"] = groups[
        "scan"
    ].game_version_selection_origin
    projection["scan.max_concurrent_scans"] = groups["scan"].max_concurrent_scans
    projection["scan.max_concurrent_scans_origin"] = groups[
        "scan"
    ].max_concurrent_scans_origin
    projection["setup.managed_game"] = groups["setup"].managed_game
    projection["setup.managed_game_origin"] = groups["setup"].managed_game_origin
    projection["setup.game_version_selection"] = groups["setup"].game_version_selection
    projection["setup.game_version_selection_origin"] = groups[
        "setup"
    ].game_version_selection_origin
    projection["setup.game_root"] = groups["setup"].game_root
    projection["setup.game_root_origin"] = groups["setup"].game_root_origin
    projection["setup.game_executable"] = groups["setup"].game_executable
    projection["setup.game_executable_origin"] = groups["setup"].game_executable_origin
    projection["setup.documents_root"] = groups["setup"].documents_root
    projection["setup.documents_root_origin"] = groups["setup"].documents_root_origin
    projection["setup.ini_folder"] = groups["setup"].ini_folder
    projection["setup.ini_folder_origin"] = groups["setup"].ini_folder_origin
    projection["setup.mods_root"] = groups["setup"].mods_root
    projection["setup.mods_root_origin"] = groups["setup"].mods_root_origin
    projection["setup.custom_scan_input"] = groups["setup"].custom_scan_input
    projection["setup.custom_scan_input_origin"] = groups[
        "setup"
    ].custom_scan_input_origin
    projection["setup.papyrus_log"] = groups["setup"].papyrus_log
    projection["setup.papyrus_log_origin"] = groups["setup"].papyrus_log_origin
    projection["preferences.auto_switch_after_scan"] = groups[
        "preferences"
    ].auto_switch_after_scan
    projection["preferences.auto_switch_after_scan_origin"] = groups[
        "preferences"
    ].auto_switch_after_scan_origin
    projection["preferences.auto_refresh_interval_ms"] = groups[
        "preferences"
    ].auto_refresh_interval_ms
    projection["preferences.auto_refresh_interval_ms_origin"] = groups[
        "preferences"
    ].auto_refresh_interval_ms_origin
    projection["tui.active_tab"] = groups["tui"].active_tab
    projection["tui.active_tab_origin"] = groups["tui"].active_tab_origin
    projection["tui.results_panel_width"] = groups["tui"].results_panel_width
    projection["tui.results_panel_width_origin"] = groups[
        "tui"
    ].results_panel_width_origin
    projection["tui.sort_ascending"] = groups["tui"].sort_ascending
    projection["tui.sort_ascending_origin"] = groups["tui"].sort_ascending_origin
    projection["main_tab.maximized"] = groups["main_tab"].maximized
    projection["main_tab.maximized_origin"] = groups["main_tab"].maximized_origin
    projection["main_tab.width"] = groups["main_tab"].width
    projection["main_tab.width_origin"] = groups["main_tab"].width_origin
    projection["main_tab.height"] = groups["main_tab"].height
    projection["main_tab.height_origin"] = groups["main_tab"].height_origin
    projection["backups_tab.maximized"] = groups["backups_tab"].maximized
    projection["backups_tab.maximized_origin"] = groups["backups_tab"].maximized_origin
    projection["backups_tab.width"] = groups["backups_tab"].width
    projection["backups_tab.width_origin"] = groups["backups_tab"].width_origin
    projection["backups_tab.height"] = groups["backups_tab"].height
    projection["backups_tab.height_origin"] = groups["backups_tab"].height_origin
    projection["articles_tab.maximized"] = groups["articles_tab"].maximized
    projection["articles_tab.maximized_origin"] = groups[
        "articles_tab"
    ].maximized_origin
    projection["articles_tab.width"] = groups["articles_tab"].width
    projection["articles_tab.width_origin"] = groups["articles_tab"].width_origin
    projection["articles_tab.height"] = groups["articles_tab"].height
    projection["articles_tab.height_origin"] = groups["articles_tab"].height_origin
    projection["results_tab.maximized"] = groups["results_tab"].maximized
    projection["results_tab.maximized_origin"] = groups["results_tab"].maximized_origin
    projection["results_tab.width"] = groups["results_tab"].width
    projection["results_tab.width_origin"] = groups["results_tab"].width_origin
    projection["results_tab.height"] = groups["results_tab"].height
    projection["results_tab.height_origin"] = groups["results_tab"].height_origin
    return {"projection": projection}
