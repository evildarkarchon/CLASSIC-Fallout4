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


class UserSettingsSnapshot:
    """Read-only User Settings snapshot from an explicit CLASSIC root."""

    @property
    def update_preferences(self) -> UpdatePreferences: ...

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


def open_user_settings(classic_root: str) -> UserSettingsSnapshot:
    """Open User Settings relative to an explicit CLASSIC root without writing."""
