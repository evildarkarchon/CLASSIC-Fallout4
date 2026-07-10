"""Typed, read-only access to CLASSIC User Settings."""

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


class UserSettingsUpdate:
    """A caller-authored request for a non-persisting User Settings Update preview."""

    def __init__(self) -> None: ...

    def set_update_check(self, value: bool) -> None:
        """Request a new Update Check preference."""

    def set_game_version_selection(self, value: str) -> None:
        """Request one canonical game-version selection token."""

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


class UserSettingsSnapshot:
    """Read-only User Settings snapshot from an explicit CLASSIC root."""

    @property
    def update_preferences(self) -> UpdatePreferences: ...

    @property
    def crash_log_scan_settings(self) -> CrashLogScanSettings: ...

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
