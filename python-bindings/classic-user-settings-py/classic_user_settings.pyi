"""Typed CLASSIC User Settings access with explicit conflict-safe commits."""

from __future__ import annotations


class UserSettingsDiagnostic:
    """One structured diagnostic produced while opening User Settings."""

    @property
    def code(self) -> str: ...

    @property
    def message(self) -> str: ...


class UpdatePreferences:
    """Update-related User Settings consumed by update-check policy."""

    @property
    def update_check(self) -> bool: ...

    @property
    def origin(self) -> str: ...


class CrashLogScanSettings:
    """Typed Crash Log Scan settings projected from User Settings."""

    @property
    def fcx_mode(self) -> bool: ...

    @property
    def fcx_mode_origin(self) -> str: ...

    @property
    def simplify_logs(self) -> bool: ...

    @property
    def simplify_logs_origin(self) -> str: ...

    @property
    def show_statistics(self) -> bool: ...

    @property
    def show_statistics_origin(self) -> str: ...

    @property
    def formid_value_lookup(self) -> bool: ...

    @property
    def formid_value_lookup_origin(self) -> str: ...

    @property
    def formid_databases(self) -> dict[str, list[str]]: ...

    @property
    def formid_databases_origin(self) -> str: ...

    @property
    def move_unsolved_logs(self) -> bool: ...

    @property
    def move_unsolved_logs_origin(self) -> str: ...

    @property
    def unsolved_logs_destination(self) -> str | None: ...

    @property
    def unsolved_logs_destination_origin(self) -> str: ...

    @property
    def custom_scan_input(self) -> str | None: ...

    @property
    def custom_scan_input_origin(self) -> str: ...

    @property
    def game_version_selection(self) -> str: ...

    @property
    def game_version_selection_origin(self) -> str: ...

    @property
    def max_concurrent_scans(self) -> int: ...

    @property
    def max_concurrent_scans_origin(self) -> str: ...


class GameSetupSettings:
    """Typed Game Setup settings projected from User Settings."""

    @property
    def managed_game(self) -> str: ...

    @property
    def managed_game_origin(self) -> str: ...

    @property
    def game_version_selection(self) -> str: ...

    @property
    def game_version_selection_origin(self) -> str: ...

    @property
    def game_root(self) -> str | None: ...

    @property
    def game_root_origin(self) -> str: ...

    @property
    def game_executable(self) -> str | None: ...

    @property
    def game_executable_origin(self) -> str: ...

    @property
    def documents_root(self) -> str | None: ...

    @property
    def documents_root_origin(self) -> str: ...

    @property
    def ini_folder(self) -> str | None: ...

    @property
    def ini_folder_origin(self) -> str: ...

    @property
    def mods_root(self) -> str | None: ...

    @property
    def mods_root_origin(self) -> str: ...

    @property
    def custom_scan_input(self) -> str | None: ...

    @property
    def custom_scan_input_origin(self) -> str: ...

    @property
    def papyrus_log(self) -> str | None: ...

    @property
    def papyrus_log_origin(self) -> str: ...


class FrontendPreferences:
    """Remembered presentation preferences shared by maintained frontends."""

    @property
    def auto_switch_after_scan(self) -> bool: ...

    @property
    def auto_switch_after_scan_origin(self) -> str: ...

    @property
    def auto_refresh_interval_ms(self) -> int: ...

    @property
    def auto_refresh_interval_ms_origin(self) -> str: ...


class WindowGeometry:
    """Widget-independent remembered geometry for one GUI tab."""

    @property
    def maximized(self) -> bool: ...

    @property
    def maximized_origin(self) -> str: ...

    @property
    def width(self) -> int: ...

    @property
    def width_origin(self) -> str: ...

    @property
    def height(self) -> int: ...

    @property
    def height_origin(self) -> str: ...


class GuiWindowGeometry:
    """Remembered geometry for every maintained GUI tab."""

    @property
    def main_tab(self) -> WindowGeometry: ...

    @property
    def backups_tab(self) -> WindowGeometry: ...

    @property
    def articles_tab(self) -> WindowGeometry: ...

    @property
    def results_tab(self) -> WindowGeometry: ...


class TuiRememberedState:
    """Remembered TUI state represented under the canonical UI.tui namespace."""

    @property
    def active_tab(self) -> int: ...

    @property
    def active_tab_origin(self) -> str: ...

    @property
    def results_panel_width(self) -> int: ...

    @property
    def results_panel_width_origin(self) -> str: ...

    @property
    def sort_ascending(self) -> bool: ...

    @property
    def sort_ascending_origin(self) -> str: ...


class FrontendState:
    """Cohesive, widget-independent User Settings state remembered by frontends."""

    @property
    def preferences(self) -> FrontendPreferences: ...

    @property
    def window_geometry(self) -> GuiWindowGeometry: ...

    @property
    def tui(self) -> TuiRememberedState: ...


class UserSettingsUpdate:
    """A caller-authored request for a non-persisting User Settings Update preview."""

    def __init__(self) -> None: ...

    def set_update_check(self, value: bool) -> None:
        """Request a new Update Check preference."""

    def set_managed_game(self, value: str) -> None:
        """Request a managed-game identifier for complete preview validation."""

    def set_game_version_selection(self, value: str) -> None:
        """Request one canonical game-version selection token."""

    def set_game_root(self, value: str | None) -> None:
        """Request an optional game installation root; None clears it."""

    def set_game_executable(self, value: str | None) -> None:
        """Request an optional game executable path; None clears it."""

    def set_documents_root(self, value: str | None) -> None:
        """Request an optional documents root; None clears it."""

    def set_ini_folder(self, value: str | None) -> None:
        """Request an optional INI-folder fallback; None clears it."""

    def set_mods_folder(self, value: str | None) -> None:
        """Request an optional mods or staging root; None clears it."""

    def set_fcx_mode(self, value: bool) -> None:
        """Request a new FCX Mode preference."""

    def set_simplify_logs(self, value: bool) -> None:
        """Request a new Simplify Logs preference."""

    def set_show_statistics(self, value: bool) -> None:
        """Request a new Show Statistics preference."""

    def set_formid_value_lookup(self, value: bool) -> None:
        """Request a new FormID Value Lookup preference."""

    def set_formid_databases(self, value: dict[str, list[str]]) -> None:
        """Request replacement FormID database paths keyed by managed game."""

    def set_move_unsolved_logs(self, value: bool) -> None:
        """Request a new Move Unsolved Logs preference."""

    def set_unsolved_logs_destination(self, value: str | None) -> None:
        """Request an optional Unsolved Logs Destination; None clears it."""

    def set_custom_scan_input(self, value: str | None) -> None:
        """Request an optional custom Crash Log Scan input; None clears it."""

    def set_papyrus_log_path(self, value: str | None) -> None:
        """Request an optional Papyrus log path; None clears it."""

    def set_max_concurrent_scans(self, value: int) -> None:
        """Request scan concurrency in the persisted 0 through 32 range."""


class UserSettingsUpdateDiagnostic:
    """One field-specific diagnostic from a rejected update preview."""

    @property
    def field_path(self) -> str | None: ...

    @property
    def code(self) -> str: ...

    @property
    def message(self) -> str: ...


class UserSettingsUpdateField:
    """One canonical field explicitly requested in an accepted update preview."""

    @property
    def canonical_path(self) -> str: ...

    @property
    def value(self) -> bool | int | str | dict[str, list[str]] | None: ...


class UserSettingsUpdatePreview:
    """All-or-nothing result of previewing a User Settings Update."""

    @property
    def accepted(self) -> bool: ...

    @property
    def base_revision(self) -> str | None: ...

    @property
    def fields(self) -> list[UserSettingsUpdateField]: ...

    @property
    def diagnostics(self) -> list[UserSettingsUpdateDiagnostic]: ...

    def commit(self, classic_root: str) -> UserSettingsCommitOutcome:
        """Commit an accepted preview or return a stale-revision conflict."""


class UserSettingsCommitOutcome:
    """Structured outcome from committing a previously accepted update."""

    @property
    def status(self) -> str: ...

    @property
    def revision(self) -> str | None: ...

    @property
    def expected_revision(self) -> str | None: ...

    @property
    def actual_revision(self) -> str | None: ...


class UserSettingsCommitError(RuntimeError):
    """Operational failure while publishing an accepted update."""


class UserSettingsSnapshot:
    """Read-only User Settings snapshot from an explicit CLASSIC root."""

    @property
    def update_preferences(self) -> UpdatePreferences: ...

    @property
    def crash_log_scan_settings(self) -> CrashLogScanSettings: ...

    @property
    def game_setup_settings(self) -> GameSetupSettings: ...

    @property
    def frontend_state(self) -> FrontendState: ...

    @property
    def source_location(self) -> str: ...

    @property
    def source_path(self) -> str | None: ...

    @property
    def classification(self) -> str: ...

    @property
    def schema_major(self) -> int | None: ...

    @property
    def schema_minor(self) -> int | None: ...

    @property
    def revision(self) -> str: ...

    @property
    def commit_eligibility(self) -> str: ...

    @property
    def diagnostics(self) -> list[UserSettingsDiagnostic]: ...

    @property
    def original_content(self) -> bytes | None: ...

    def preview_update(self, update: UserSettingsUpdate) -> UserSettingsUpdatePreview:
        """Validate every requested field as one unit without writing."""


def open_user_settings(classic_root: str) -> UserSettingsSnapshot:
    """Open User Settings relative to an explicit CLASSIC root without writing."""
