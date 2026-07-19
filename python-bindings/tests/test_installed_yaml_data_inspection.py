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
    b"exclude_log_records:\r\n"
    b'  - "(void*)"\r\n'
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
DEFAULT_IGNORE_BYTES = b"CLASSIC_Ignore_Fallout4:\n  - SelectedMainDefault.dll\n"
MAIN_WITH_DEFAULT_BYTES = (
    b'schema_version: "2.0"\n'
    b"CLASSIC_Info:\n"
    b'  version: "9.1.0"\n'
    b"  default_ignorefile: |\n"
    b"    CLASSIC_Ignore_Fallout4:\n"
    b"      - SelectedMainDefault.dll\n"
    b"CLASSIC_Interface:\n"
    b'  autoscan_text_Fallout4: "bundled"\n'
)


def write_install(
    root: Path, *, with_ignore: bool = False, main_bytes: bytes = MAIN_BYTES
) -> None:
    """Write minimum valid bundled data and, when requested, Local Ignore data."""
    databases = root / "CLASSIC Data" / "databases"
    databases.mkdir(parents=True)
    (databases / "CLASSIC Main.yaml").write_bytes(main_bytes)
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
    assert snapshot.simplify_remove_list == ["(void*)"]
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


def test_installed_load_projects_generated_local_ignore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing Local Ignore becomes a Ready snapshot with generated provenance."""
    installation = tmp_path / "install"
    write_install(installation, main_bytes=MAIN_WITH_DEFAULT_BYTES)
    isolate_cache(monkeypatch, tmp_path / "cache-root")
    ignore_path = installation / "CLASSIC Data" / "CLASSIC Ignore.yaml"

    outcome = classic_config.load_installed_yaml_data(
        installation,
        classic_config.ExplicitYamlDataGame.FALLOUT4,
        "Original",
    )

    assert outcome.status == "ready"
    snapshot = outcome.snapshot
    assert snapshot.local_ignore_state == "generated"
    assert snapshot.yaml_data.ignore_list == ["SelectedMainDefault.dll"]
    assert snapshot.local_ignore_identity.sha256 == hashlib.sha256(
        DEFAULT_IGNORE_BYTES
    ).hexdigest()
    assert snapshot.local_ignore_identity.byte_len == len(DEFAULT_IGNORE_BYTES)
    assert ignore_path.read_bytes() == DEFAULT_IGNORE_BYTES
    generated = snapshot.diagnostics[-1]
    assert generated.role is None
    assert generated.candidate is None
    assert generated.path == ignore_path
    assert generated.kind == "local_ignore_generated"


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


def test_installed_load_keeps_invalid_defaults_fatal_only_while_ignore_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid defaults do not block recovery from malformed installed Local Ignore."""
    installation = tmp_path / "install"
    write_install(installation)
    isolate_cache(monkeypatch, tmp_path / "cache-root")
    ignore_path = installation / "CLASSIC Data" / "CLASSIC Ignore.yaml"

    with pytest.raises(
        classic_config.InstalledYamlDataLoadLocalIgnoreDefaultInvalidError
    ) as exc_info:
        classic_config.load_installed_yaml_data(
            installation,
            classic_config.ExplicitYamlDataGame.FALLOUT4,
            "Original",
        )
    assert exc_info.value.code == "local_ignore_default_invalid"
    assert exc_info.value.yaml_role == "local_ignore"
    assert exc_info.value.path == str(ignore_path)
    assert exc_info.value.diagnostics == []

    malformed_ignore = b"CLASSIC_Ignore_Fallout4: not-a-sequence\n"
    ignore_path.write_bytes(malformed_ignore)
    databases = installation / "CLASSIC Data" / "databases"
    main_path = databases / "CLASSIC Main.yaml"
    game_path = databases / "CLASSIC Fallout4.yaml"
    original_files = {
        path: path.read_bytes() for path in (main_path, game_path, ignore_path)
    }

    outcome = classic_config.load_installed_yaml_data(
        installation,
        classic_config.ExplicitYamlDataGame.FALLOUT4,
        "Original",
    )
    assert isinstance(
        outcome,
        classic_config.InstalledYamlDataLocalIgnoreRecoveryRequiredOutcome,
    )
    plan = outcome.recovery_plan
    assert plan.default_local_ignore_identity is None

    snapshot = plan.proceed_without_ignore()
    assert snapshot.local_ignore_state == "proceed_without_ignore"
    assert snapshot.yaml_data.ignore_list == []
    assert {path: path.read_bytes() for path in original_files} == original_files

    later_outcome = classic_config.load_installed_yaml_data(
        installation,
        classic_config.ExplicitYamlDataGame.FALLOUT4,
        "Original",
    )
    assert isinstance(
        later_outcome,
        classic_config.InstalledYamlDataLocalIgnoreRecoveryRequiredOutcome,
    )
    assert later_outcome.recovery_plan.default_local_ignore_identity is None
    assert {path: path.read_bytes() for path in original_files} == original_files


@pytest.mark.parametrize(
    ("ignore_bytes", "diagnostic_kind"),
    [
        (b"\xff", "invalid_utf8"),
        (b"CLASSIC_Ignore_Fallout4: [unterminated", "parse"),
        (b"CLASSIC_Ignore_Fallout4: not-a-sequence\n", "invalid_role_data"),
    ],
)
def test_installed_load_projects_consumable_local_ignore_recovery_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ignore_bytes: bytes,
    diagnostic_kind: str,
) -> None:
    """Malformed Local Ignore data can be ignored once without mutating installed files."""
    installation = tmp_path / "install"
    write_install(installation, main_bytes=MAIN_WITH_DEFAULT_BYTES)
    isolate_cache(monkeypatch, tmp_path / "cache-root")
    databases = installation / "CLASSIC Data" / "databases"
    main_path = databases / "CLASSIC Main.yaml"
    game_path = databases / "CLASSIC Fallout4.yaml"
    ignore_path = installation / "CLASSIC Data" / "CLASSIC Ignore.yaml"
    ignore_path.write_bytes(ignore_bytes)
    original_files = {
        path: path.read_bytes() for path in (main_path, game_path, ignore_path)
    }

    outcome = classic_config.load_installed_yaml_data(
        installation,
        classic_config.ExplicitYamlDataGame.FALLOUT4,
        "Original",
    )
    assert {path: path.read_bytes() for path in original_files} == original_files

    assert isinstance(
        outcome,
        classic_config.InstalledYamlDataLocalIgnoreRecoveryRequiredOutcome,
    )
    assert outcome.status == "local_ignore_recovery_required"
    plan = outcome.recovery_plan
    assert plan.game == classic_config.ExplicitYamlDataGame.FALLOUT4
    assert plan.game_data_role == "Fallout4"
    assert plan.main.sha256 == hashlib.sha256(MAIN_WITH_DEFAULT_BYTES).hexdigest()
    assert plan.game_file.sha256 == hashlib.sha256(GAME_BYTES).hexdigest()
    assert plan.local_ignore_path == ignore_path
    assert plan.malformed_local_ignore_identity.sha256 == hashlib.sha256(
        ignore_bytes
    ).hexdigest()
    assert plan.malformed_local_ignore_identity.byte_len == len(ignore_bytes)
    default_identity = plan.default_local_ignore_identity
    assert default_identity is not None
    assert default_identity.sha256 == hashlib.sha256(DEFAULT_IGNORE_BYTES).hexdigest()
    assert default_identity.byte_len == len(DEFAULT_IGNORE_BYTES)
    assert plan.selected_game_version == "Original"
    malformed_diagnostic = plan.diagnostics[-1]
    assert malformed_diagnostic.role is None
    assert malformed_diagnostic.candidate is None
    assert malformed_diagnostic.path == ignore_path
    assert malformed_diagnostic.kind == diagnostic_kind
    retained_main_sha256 = plan.main.sha256
    retained_game_sha256 = plan.game_file.sha256
    malformed_sha256 = plan.malformed_local_ignore_identity.sha256
    replacement_main = MAIN_WITH_DEFAULT_BYTES.replace(b'"9.1.0"', b'"9.2.0"')
    replacement_game = GAME_BYTES.replace(b'"Fallout 4"', b'"Fallout4"')
    main_path.write_bytes(replacement_main)
    game_path.write_bytes(replacement_game)
    files_before_proceed = {
        path: path.read_bytes() for path in (main_path, game_path, ignore_path)
    }

    snapshot = plan.proceed_without_ignore()

    assert snapshot.local_ignore_state == "proceed_without_ignore"
    assert snapshot.yaml_data.ignore_list == []
    assert snapshot.yaml_data.classic_version == "9.1.0"
    assert snapshot.yaml_data.game_root_name == "Fallout 4"
    assert snapshot.main.sha256 == retained_main_sha256
    assert snapshot.game_file.sha256 == retained_game_sha256
    assert snapshot.local_ignore_identity.sha256 == malformed_sha256
    assert {
        path: path.read_bytes() for path in files_before_proceed
    } == files_before_proceed

    with pytest.raises(
        RuntimeError, match="Local Ignore recovery plan has already been consumed"
    ):
        plan.proceed_without_ignore()
    with pytest.raises(
        RuntimeError, match="Local Ignore recovery plan has already been consumed"
    ):
        _ = plan.game

    later_outcome = classic_config.load_installed_yaml_data(
        installation,
        classic_config.ExplicitYamlDataGame.FALLOUT4,
        "Original",
    )
    assert isinstance(
        later_outcome,
        classic_config.InstalledYamlDataLocalIgnoreRecoveryRequiredOutcome,
    )
    assert (
        later_outcome.recovery_plan.malformed_local_ignore_identity.sha256
        == snapshot.local_ignore_identity.sha256
    )
    assert later_outcome.recovery_plan.main.sha256 == hashlib.sha256(
        replacement_main
    ).hexdigest()
    assert later_outcome.recovery_plan.game_file.sha256 == hashlib.sha256(
        replacement_game
    ).hexdigest()
    assert {
        path: path.read_bytes() for path in files_before_proceed
    } == files_before_proceed


def test_local_ignore_reset_projects_durable_success_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reset exposes the durable backup, replacement identities, and retained snapshot."""
    installation = tmp_path / "install"
    write_install(installation, main_bytes=MAIN_WITH_DEFAULT_BYTES)
    isolate_cache(monkeypatch, tmp_path / "cache-root")
    ignore_path = installation / "CLASSIC Data" / "CLASSIC Ignore.yaml"
    malformed_bytes = b"CLASSIC_Ignore_Fallout4: not-a-sequence\r\n"
    ignore_path.write_bytes(malformed_bytes)

    load_outcome = classic_config.load_installed_yaml_data(
        installation,
        classic_config.ExplicitYamlDataGame.FALLOUT4,
        "Original",
    )
    plan = load_outcome.recovery_plan
    reset_outcome = plan.reset_to_default()

    assert isinstance(reset_outcome, classic_config.LocalIgnoreResetOutcome)
    assert reset_outcome.status == "reset"
    assert reset_outcome.local_ignore_path == ignore_path
    assert reset_outcome.backup_path.read_bytes() == malformed_bytes
    assert ignore_path.read_bytes() == DEFAULT_IGNORE_BYTES
    malformed_sha256 = hashlib.sha256(malformed_bytes).hexdigest()
    replacement_sha256 = hashlib.sha256(DEFAULT_IGNORE_BYTES).hexdigest()
    assert reset_outcome.malformed_local_ignore_identity.sha256 == malformed_sha256
    assert reset_outcome.backup_identity.sha256 == malformed_sha256
    assert reset_outcome.replacement_identity.sha256 == replacement_sha256
    assert reset_outcome.snapshot.local_ignore_state == "reset_to_default"
    assert reset_outcome.snapshot.local_ignore_identity.sha256 == replacement_sha256
    assert reset_outcome.snapshot.yaml_data.ignore_list == ["SelectedMainDefault.dll"]
    reset_diagnostic = reset_outcome.diagnostics[-1]
    assert reset_diagnostic.path == ignore_path
    assert reset_diagnostic.kind == "local_ignore_reset"

    with pytest.raises(
        RuntimeError, match="Local Ignore recovery plan has already been consumed"
    ):
        plan.reset_to_default()


def test_local_ignore_reset_projects_conflict_without_overwriting_newer_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A changed canonical file returns typed identity metadata and is never overwritten."""
    installation = tmp_path / "install"
    write_install(installation, main_bytes=MAIN_WITH_DEFAULT_BYTES)
    isolate_cache(monkeypatch, tmp_path / "cache-root")
    ignore_path = installation / "CLASSIC Data" / "CLASSIC Ignore.yaml"
    malformed_bytes = b"CLASSIC_Ignore_Fallout4: not-a-sequence\n"
    changed_bytes = b"CLASSIC_Ignore_Fallout4:\n  - NewerUserEdit.dll\n"
    ignore_path.write_bytes(malformed_bytes)

    load_outcome = classic_config.load_installed_yaml_data(
        installation,
        classic_config.ExplicitYamlDataGame.FALLOUT4,
        "Original",
    )
    plan = load_outcome.recovery_plan
    ignore_path.write_bytes(changed_bytes)
    conflict = plan.reset_to_default()

    assert isinstance(conflict, classic_config.LocalIgnoreResetConflictOutcome)
    assert conflict.status == "conflict"
    assert conflict.expected_identity.sha256 == hashlib.sha256(
        malformed_bytes
    ).hexdigest()
    assert conflict.actual_identity is not None
    assert conflict.actual_identity.sha256 == hashlib.sha256(changed_bytes).hexdigest()
    assert conflict.backup_path is None
    assert ignore_path.read_bytes() == changed_bytes
    assert not (installation / "CLASSIC Backup").exists()

    with pytest.raises(
        RuntimeError, match="Local Ignore recovery plan has already been consumed"
    ):
        plan.proceed_without_ignore()


def test_local_ignore_reset_projects_defaults_unavailable_and_error_hierarchy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every reset failure remains catchable through a typed operational hierarchy."""
    installation = tmp_path / "install"
    write_install(installation)
    isolate_cache(monkeypatch, tmp_path / "cache-root")
    ignore_path = installation / "CLASSIC Data" / "CLASSIC Ignore.yaml"
    malformed_bytes = b"CLASSIC_Ignore_Fallout4: not-a-sequence\n"
    ignore_path.write_bytes(malformed_bytes)

    load_outcome = classic_config.load_installed_yaml_data(
        installation,
        classic_config.ExplicitYamlDataGame.FALLOUT4,
        "Original",
    )
    plan = load_outcome.recovery_plan
    with pytest.raises(
        classic_config.LocalIgnoreResetDefaultsUnavailableError
    ) as exc_info:
        plan.reset_to_default()

    assert isinstance(exc_info.value, classic_config.LocalIgnoreResetError)
    assert exc_info.value.code == "defaults_unavailable"
    assert exc_info.value.path == str(ignore_path)
    assert exc_info.value.stage is None
    assert exc_info.value.reason
    assert ignore_path.read_bytes() == malformed_bytes
    with pytest.raises(
        RuntimeError, match="Local Ignore recovery plan has already been consumed"
    ):
        plan.reset_to_default()

    for error_type in (
        classic_config.LocalIgnoreResetDefaultsUnavailableError,
        classic_config.LocalIgnoreResetLockError,
        classic_config.LocalIgnoreResetReadError,
        classic_config.LocalIgnoreResetBackupDirectoryError,
        classic_config.LocalIgnoreResetBackupPublicationError,
        classic_config.LocalIgnoreResetBackupVerificationError,
        classic_config.LocalIgnoreResetReplacementPublicationError,
    ):
        assert issubclass(error_type, classic_config.LocalIgnoreResetError)


def test_installed_load_exports_local_ignore_create_failure_type() -> None:
    """Atomic publication failures remain a dedicated typed public error."""
    assert issubclass(
        classic_config.InstalledYamlDataLoadLocalIgnoreCreateError,
        classic_config.InstalledYamlDataLoadError,
    )


def test_installed_load_exports_invalid_selected_data_failure_type() -> None:
    """The defensive post-selection projection failure remains a typed public error."""
    assert issubclass(
        classic_config.InstalledYamlDataLoadInvalidSelectedDataError,
        classic_config.InstalledYamlDataLoadError,
    )
