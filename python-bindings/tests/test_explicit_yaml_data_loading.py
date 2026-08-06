"""Focused public-contract tests for deterministic explicit YAML Data loading."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import classic_config


MAIN_BYTES = (
    b'schema_version: "2.0"\r\n'
    b"CLASSIC_Info:\r\n"
    b'  version: "9.1.0"\r\n'
    b"CLASSIC_Interface:\r\n"
    b'  autoscan_text_Fallout4: "explicit python"\r\n'
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
EMPTY_IGNORE_BYTES = b"CLASSIC_Ignore_Fallout4: []\n"


def write_explicit_files(
    root: Path, ignore: bytes = EMPTY_IGNORE_BYTES
) -> classic_config.ExplicitYamlDataPaths:
    """Write arbitrary-name fixtures and return the public typed path request."""
    main_path = root / "chosen-main.fixture"
    game_path = root / "chosen-game.fixture"
    ignore_path = root / "chosen-ignore.fixture"
    main_path.write_bytes(MAIN_BYTES)
    game_path.write_bytes(GAME_BYTES)
    ignore_path.write_bytes(ignore)
    return classic_config.ExplicitYamlDataPaths(main_path, game_path, ignore_path)


def test_explicit_loader_owns_exact_bytes_and_maps_vr_to_fallout4(tmp_path: Path) -> None:
    """The snapshot keeps parsed data and identity tied to the original bytes."""
    paths = write_explicit_files(tmp_path)
    snapshot = classic_config.load_explicit_yaml_data(
        paths,
        classic_config.ExplicitYamlDataGame.FALLOUT4_VR,
        "VR",
    )

    assert snapshot.game == classic_config.ExplicitYamlDataGame.FALLOUT4_VR
    assert snapshot.game_data_role == "Fallout4"
    assert snapshot.yaml_data.classic_version == "9.1.0"
    assert snapshot.yaml_data.ignore_list == []
    assert snapshot.main_identity.byte_len == len(MAIN_BYTES)
    assert snapshot.main_identity.sha256 == hashlib.sha256(MAIN_BYTES).hexdigest()
    assert snapshot.ignore_identity.byte_len == len(EMPTY_IGNORE_BYTES)

    paths.main_path.write_bytes(b"replacement bytes")
    assert snapshot.yaml_data.classic_version == "9.1.0"
    assert snapshot.main_identity.sha256 == hashlib.sha256(MAIN_BYTES).hexdigest()


def test_explicit_loader_exposes_typed_unsupported_and_ignore_failures(
    tmp_path: Path,
) -> None:
    """Unsupported games and malformed Local Ignore data stay distinguishable."""
    missing = classic_config.ExplicitYamlDataPaths(
        tmp_path / "missing-main",
        tmp_path / "missing-game",
        tmp_path / "missing-ignore",
    )
    with pytest.raises(classic_config.ExplicitYamlDataUnsupportedGameError) as unsupported_info:
        classic_config.load_explicit_yaml_data(
            missing,
            classic_config.ExplicitYamlDataGame.SKYRIM,
            "AnniversaryEdition",
        )
    assert unsupported_info.value.code == "unsupported_game"
    assert unsupported_info.value.yaml_role is None
    assert unsupported_info.value.path is None

    malformed = write_explicit_files(
        tmp_path,
        b"CLASSIC_Ignore_Fallout4: not-a-sequence\n",
    )
    with pytest.raises(classic_config.ExplicitYamlDataInvalidRoleDataError) as exc_info:
        classic_config.load_explicit_yaml_data(
            malformed,
            classic_config.ExplicitYamlDataGame.FALLOUT4,
            "Original",
        )
    assert "Local Ignore" in str(exc_info.value)
    assert str(malformed.ignore_path) in str(exc_info.value)
    assert exc_info.value.code == "invalid_role_data"
    assert exc_info.value.yaml_role == "local_ignore"
    assert exc_info.value.path == str(malformed.ignore_path)


def test_explicit_loader_does_not_generate_a_missing_ignore_file(tmp_path: Path) -> None:
    """A missing exact Local Ignore path stays missing after the typed read error."""
    paths = write_explicit_files(tmp_path)
    paths.ignore_path.unlink()

    with pytest.raises(classic_config.ExplicitYamlDataReadError):
        classic_config.load_explicit_yaml_data(
            paths,
            classic_config.ExplicitYamlDataGame.FALLOUT4,
            "Original",
        )
    assert not paths.ignore_path.exists()
