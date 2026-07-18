"""Focused contract tests for Installed YAML Data inspection."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

import classic_config


MAIN_BYTES = (
    b'schema_version: "2.0"\r\n'
    b"CLASSIC_Info:\r\n"
    b'  version: "9.1.0"\r\n'
    b"CLASSIC_Interface:\r\n"
    b'  autoscan_text_Fallout4: "bundled"\r\n'
)
GAME_BYTES = (
    b'schema_version: "1.0"\n'
    b"Game_Info:\n"
    b'  Main_Root_Name: "Fallout 4"\n'
    b"Crashlog_Error_Check: []\n"
    b"Crashlog_Stack_Check: []\n"
    b"Mods_FREQ: []\n"
    b"Mods_SOLU: []\n"
)
IGNORE_BYTES = b"CLASSIC_Ignore_Fallout4:\r\n  - ExistingUserEntry.dll\r\n"


def write_install(root: Path, *, with_ignore: bool = False) -> None:
    """Write minimum valid bundled data and, when requested, Local Ignore data."""
    databases = root / "CLASSIC Data" / "databases"
    databases.mkdir(parents=True)
    (databases / "CLASSIC Main.yaml").write_bytes(MAIN_BYTES)
    (databases / "CLASSIC Fallout4.yaml").write_bytes(GAME_BYTES)
    if with_ignore:
        (root / "CLASSIC Data" / "CLASSIC Ignore.yaml").write_bytes(IGNORE_BYTES)


def isolate_cache(monkeypatch: pytest.MonkeyPatch, root: Path) -> Path:
    """Point the platform cache resolver at one test-owned directory."""
    if os.name == "nt":
        monkeypatch.setenv("LOCALAPPDATA", str(root))
        monkeypatch.delenv("APPDATA", raising=False)
    else:
        monkeypatch.setenv("XDG_CACHE_HOME", str(root))
        monkeypatch.delenv("HOME", raising=False)
    return root / "CLASSIC" / "yaml-cache"


def test_inspection_projects_independent_selection_and_exact_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Selected Main/game facts retain independent provenance and exact-byte identity."""
    installation = tmp_path / "install"
    write_install(installation)
    cache = isolate_cache(monkeypatch, tmp_path / "cache-root")
    cache.mkdir(parents=True)
    updated_main = MAIN_BYTES.replace(b"bundled", b"updated cache")
    (cache / "CLASSIC Main.yaml").write_bytes(updated_main)
    ignored_path = installation / "CLASSIC Data" / "CLASSIC Ignore.yaml"
    ignored_bytes = b"not: [valid YAML Data"
    ignored_path.write_bytes(ignored_bytes)

    result = classic_config.inspect_installed_yaml_data(
        installation,
        classic_config.ExplicitYamlDataGame.FALLOUT4_VR,
    )

    assert result.game == classic_config.ExplicitYamlDataGame.FALLOUT4_VR
    assert result.game_data_role == "Fallout4"
    assert result.main.role == "main"
    assert result.main.provenance == "updated"
    assert (result.main.schema_major, result.main.schema_minor) == (2, 0)
    assert result.main.sha256 == hashlib.sha256(updated_main).hexdigest()
    assert result.main.byte_length == len(updated_main)
    assert result.game_file.role == "game"
    assert result.game_file.provenance == "bundled"
    assert (result.game_file.schema_major, result.game_file.schema_minor) == (1, 0)
    assert result.game_file.sha256 == hashlib.sha256(GAME_BYTES).hexdigest()
    assert result.diagnostics == []
    assert ignored_path.read_bytes() == ignored_bytes


def test_inspection_preserves_rejection_diagnostics_on_bundled_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An incompatible canonical cache file is attributed without being modified."""
    installation = tmp_path / "install"
    write_install(installation)
    cache = isolate_cache(monkeypatch, tmp_path / "cache-root")
    cache.mkdir(parents=True)
    incompatible = MAIN_BYTES.replace(b'"2.0"', b'"99.0"')
    updated_path = cache / "CLASSIC Main.yaml"
    updated_path.write_bytes(incompatible)

    result = classic_config.inspect_installed_yaml_data(
        installation,
        classic_config.ExplicitYamlDataGame.FALLOUT4,
    )

    assert result.main.provenance == "bundled"
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.role == "main"
    assert diagnostic.candidate == "updated"
    assert diagnostic.path == updated_path
    assert diagnostic.kind == "incompatible_schema"
    assert "99.0" in diagnostic.message
    assert updated_path.read_bytes() == incompatible


def test_inspection_exposes_typed_terminal_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unsupported games and exhausted sources remain separately catchable."""
    isolate_cache(monkeypatch, tmp_path / "cache-root")

    with pytest.raises(classic_config.InstalledYamlDataUnsupportedGameError) as unsupported:
        classic_config.inspect_installed_yaml_data(
            tmp_path / "missing",
            classic_config.ExplicitYamlDataGame.SKYRIM,
        )
    assert unsupported.value.code == "unsupported_game"
    assert unsupported.value.yaml_role is None
    assert unsupported.value.diagnostics == []

    with pytest.raises(classic_config.InstalledYamlDataNoUsableSourceError) as unavailable:
        classic_config.inspect_installed_yaml_data(
            tmp_path / "missing",
            classic_config.ExplicitYamlDataGame.FALLOUT4,
        )
    assert unavailable.value.code == "no_usable_source"
    assert unavailable.value.yaml_role == "main"
    assert len(unavailable.value.diagnostics) == 1
    diagnostic = unavailable.value.diagnostics[0]
    assert diagnostic.role == "main"
    assert diagnostic.candidate == "bundled"
    assert diagnostic.kind == "missing"


def test_installed_load_projects_ready_immutable_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A valid load exposes one stable snapshot of independently selected bytes."""
    installation = tmp_path / "install"
    write_install(installation, with_ignore=True)
    cache = isolate_cache(monkeypatch, tmp_path / "cache-root")
    cache.mkdir(parents=True)
    updated_main = MAIN_BYTES.replace(b"bundled", b"updated cache")
    (cache / "CLASSIC Main.yaml").write_bytes(updated_main)
    (cache / "CLASSIC Fallout4.yaml").write_bytes(
        GAME_BYTES.replace(b'"Fallout 4"', b'"Skyrim"')
    )

    outcome = classic_config.load_installed_yaml_data(
        installation,
        classic_config.ExplicitYamlDataGame.FALLOUT4_VR,
        "VR",
    )
    assert outcome.status == "ready"
    snapshot = outcome.snapshot

    assert snapshot.game == classic_config.ExplicitYamlDataGame.FALLOUT4_VR
    assert snapshot.game_data_role == "Fallout4"
    assert snapshot.yaml_data.classic_version == "9.1.0"
    assert snapshot.yaml_data.ignore_list == ["ExistingUserEntry.dll"]
    assert snapshot.main.provenance == "updated"
    assert snapshot.main.sha256 == hashlib.sha256(updated_main).hexdigest()
    assert snapshot.game_file.provenance == "bundled"
    assert snapshot.game_file.sha256 == hashlib.sha256(GAME_BYTES).hexdigest()
    assert snapshot.local_ignore_state == "existing"
    assert snapshot.local_ignore_identity.sha256 == hashlib.sha256(IGNORE_BYTES).hexdigest()
    assert snapshot.local_ignore_identity.byte_len == len(IGNORE_BYTES)
    assert [(diagnostic.role, diagnostic.kind) for diagnostic in snapshot.diagnostics] == [
        ("game", "invalid_role_data")
    ]

    (cache / "CLASSIC Main.yaml").write_bytes(b"changed after loading")
    (installation / "CLASSIC Data" / "databases" / "CLASSIC Fallout4.yaml").write_bytes(
        b"changed after loading"
    )
    (installation / "CLASSIC Data" / "CLASSIC Ignore.yaml").write_bytes(
        b"changed after loading"
    )
    assert snapshot.yaml_data.classic_version == "9.1.0"
    assert snapshot.yaml_data.game_root_name == "Fallout 4"
    assert snapshot.yaml_data.ignore_list == ["ExistingUserEntry.dll"]
    assert snapshot.local_ignore_identity.sha256 == hashlib.sha256(IGNORE_BYTES).hexdigest()


def test_installed_load_projects_selection_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Typed selection failures retain stable codes, roles, paths, and diagnostics."""
    isolate_cache(monkeypatch, tmp_path / "cache-root")

    with pytest.raises(
        classic_config.InstalledYamlDataLoadUnsupportedGameError
    ) as unsupported:
        classic_config.load_installed_yaml_data(
            tmp_path / "missing",
            classic_config.ExplicitYamlDataGame.SKYRIM,
            "AnniversaryEdition",
        )
    assert unsupported.value.code == "unsupported_game"
    assert unsupported.value.yaml_role is None
    assert unsupported.value.path is None
    assert unsupported.value.diagnostics == []

    with pytest.raises(
        classic_config.InstalledYamlDataLoadNoUsableSourceError
    ) as unavailable:
        classic_config.load_installed_yaml_data(
            tmp_path / "missing",
            classic_config.ExplicitYamlDataGame.FALLOUT4,
            "Original",
        )
    assert unavailable.value.code == "no_usable_source"
    assert unavailable.value.yaml_role == "main"
    assert unavailable.value.path is None
    assert len(unavailable.value.diagnostics) == 1
    assert unavailable.value.diagnostics[0].kind == "missing"


@pytest.mark.parametrize(
    ("ignore_bytes", "exception_name", "code"),
    [
        (None, "InstalledYamlDataLoadLocalIgnoreReadError", "local_ignore_read"),
        (
            b"\xff",
            "InstalledYamlDataLoadLocalIgnoreInvalidUtf8Error",
            "local_ignore_invalid_utf8",
        ),
        (
            b"CLASSIC_Ignore_Fallout4: [unterminated",
            "InstalledYamlDataLoadLocalIgnoreParseError",
            "local_ignore_parse",
        ),
        (
            b"CLASSIC_Ignore_Fallout4: not-a-sequence\n",
            "InstalledYamlDataLoadLocalIgnoreInvalidRoleDataError",
            "local_ignore_invalid_role_data",
        ),
    ],
)
def test_installed_load_projects_local_ignore_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ignore_bytes: bytes | None,
    exception_name: str,
    code: str,
) -> None:
    """Every Local Ignore fatal result is separately catchable with path metadata."""
    installation = tmp_path / "install"
    write_install(installation)
    isolate_cache(monkeypatch, tmp_path / "cache-root")
    ignore_path = installation / "CLASSIC Data" / "CLASSIC Ignore.yaml"
    if ignore_bytes is not None:
        ignore_path.write_bytes(ignore_bytes)

    exception_type = getattr(classic_config, exception_name)
    with pytest.raises(exception_type) as exc_info:
        classic_config.load_installed_yaml_data(
            installation,
            classic_config.ExplicitYamlDataGame.FALLOUT4,
            "Original",
        )
    assert exc_info.value.code == code
    assert exc_info.value.yaml_role == "local_ignore"
    assert exc_info.value.path == str(ignore_path)
    assert exc_info.value.diagnostics == []


def test_installed_load_exports_invalid_selected_data_failure_type() -> None:
    """The defensive post-selection projection failure remains a typed public error."""
    assert issubclass(
        classic_config.InstalledYamlDataLoadInvalidSelectedDataError,
        classic_config.InstalledYamlDataLoadError,
    )
