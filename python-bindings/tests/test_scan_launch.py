"""Public contract tests for Crash Log Scan Launch on the ``classic_scanlog`` facade."""

from pathlib import Path

import pytest

import classic_scanlog
import classic_shared

MANAGED_FALLOUT4 = """schema_version: "1.0"
CLASSIC_Settings:
  Managed Game: Fallout 4
  Game Version: NextGen
  Max Concurrent Scans: 3
  FormID Databases:
    Fallout4:
      - databases/Fallout4 FormIDs.db
"""


def _root_with_settings(tmp_path: Path, yaml: str) -> Path:
    """Write ``yaml`` as the canonical User Settings document of a fresh Installation Root."""
    (tmp_path / "CLASSIC Settings.yaml").write_text(yaml, encoding="utf-8")
    return tmp_path


def test_standard_launch_carries_the_rust_built_request_without_writing(tmp_path: Path) -> None:
    root = _root_with_settings(tmp_path, MANAGED_FALLOUT4)
    before = (root / "CLASSIC Settings.yaml").read_bytes()

    launch = classic_scanlog.ScanRunLaunch.standard(
        str(root),
        classic_scanlog.ScanRunLaunchOverrides(max_concurrent=0, show_formid_values=True),
    )

    assert launch.intent == "standard"
    assert launch.game == classic_shared.GameId.Fallout4
    assert launch.game_version == "NextGen"
    assert launch.max_concurrent is None
    assert launch.show_formid_values is True
    assert launch.formid_database_paths == ["databases/Fallout4 FormIDs.db"]
    assert launch.base_directory == str(root)
    assert launch.targeted_inputs is None
    assert launch.fcx_enabled is False
    assert launch.diagnostics == []
    assert isinstance(launch.request(), classic_scanlog.ScanRunRequest)
    assert (root / "CLASSIC Settings.yaml").read_bytes() == before


def test_degraded_user_settings_still_launch_with_their_diagnostics(tmp_path: Path) -> None:
    root = _root_with_settings(tmp_path, "CLASSIC_Settings:\n  Managed Game: Fallout 4\n")

    launch = classic_scanlog.ScanRunLaunch.standard(str(root))

    assert [(item.kind, item.code) for item in launch.diagnostics] == [
        ("user_settings", "migration_required_unversioned_document")
    ]


def test_targeted_launch_without_inputs_raises_the_typed_error(tmp_path: Path) -> None:
    root = _root_with_settings(tmp_path, MANAGED_FALLOUT4)

    with pytest.raises(classic_scanlog.ScanRunLaunchTargetedWithoutInputsError) as caught:
        classic_scanlog.ScanRunLaunch.targeted(str(root), [])

    assert isinstance(caught.value, classic_scanlog.ScanRunLaunchError)


def test_fcx_mode_override_carries_the_setup_context_with_the_xse_log(tmp_path: Path) -> None:
    game = tmp_path / "Fallout 4"
    documents = tmp_path / "Documents"
    (documents / "F4SE").mkdir(parents=True)
    xse_log = documents / "F4SE" / "f4se.log"
    xse_log.write_bytes(b"")
    root = _root_with_settings(
        tmp_path,
        MANAGED_FALLOUT4
        + f"  Game Folder Path: '{game}'\n  Documents Folder Path: '{documents}'\n",
    )

    launch = classic_scanlog.ScanRunLaunch.targeted(
        str(root),
        [str(root / "crash-one.log")],
        classic_scanlog.ScanRunLaunchOverrides(fcx_mode=True),
    )

    assert launch.fcx_enabled is True
    context = launch.setup_context
    assert context is not None
    assert Path(context.game_root) == game
    assert Path(context.docs_root) == documents
    # Nothing is saved for the executable, so NextGen's own executable under the game folder.
    assert Path(context.game_exe_path) == game / "Fallout4.exe"
    assert Path(context.xse_log_path) == xse_log


def test_uninspectable_xse_log_raises_the_typed_error(tmp_path: Path) -> None:
    # The YAML `\0` escape saves a documents folder no platform can inspect.
    root = _root_with_settings(
        tmp_path,
        MANAGED_FALLOUT4 + '  FCX Mode: true\n  Documents Folder Path: "/bad\\0docs"\n',
    )

    with pytest.raises(classic_scanlog.ScanRunLaunchXseLogInspectError) as caught:
        classic_scanlog.ScanRunLaunch.standard(str(root))

    assert isinstance(caught.value, classic_scanlog.ScanRunLaunchError)


def test_unknown_game_version_override_is_rejected() -> None:
    with pytest.raises(ValueError):
        classic_scanlog.ScanRunLaunchOverrides(game_version="Nonsense")
