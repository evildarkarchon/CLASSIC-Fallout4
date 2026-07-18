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


def write_install(root: Path) -> None:
    """Write the minimum semantically valid bundled Main and Fallout 4 data."""
    databases = root / "CLASSIC Data" / "databases"
    databases.mkdir(parents=True)
    (databases / "CLASSIC Main.yaml").write_bytes(MAIN_BYTES)
    (databases / "CLASSIC Fallout4.yaml").write_bytes(GAME_BYTES)


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
