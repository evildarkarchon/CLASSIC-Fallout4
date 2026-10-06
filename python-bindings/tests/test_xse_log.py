"""Outcome carriers of ``classic_xse.resolve_xse_log_for_scan``.

The XSE log rules (folder precedence, per-edition log names, absence) are
pinned by the Rust tests and the ``xse-folder`` conformance pack; these tests
only check how the Python binding carries each of the three outcomes.
"""

from pathlib import Path

import pytest

import classic_xse


def test_returns_the_located_log_path(tmp_path: Path) -> None:
    data = tmp_path / "CLASSIC Data"
    data.mkdir()
    xse_folder = tmp_path / "docs" / "F4SE"
    xse_folder.mkdir(parents=True)
    (xse_folder / "f4sevr.log").write_bytes(b"")

    located = classic_xse.resolve_xse_log_for_scan(
        str(data), "Fallout4VR", "auto", str(tmp_path / "docs")
    )

    assert located == str(xse_folder / "f4sevr.log")


def test_returns_none_when_the_log_is_missing(tmp_path: Path) -> None:
    data = tmp_path / "CLASSIC Data"
    data.mkdir()

    assert (
        classic_xse.resolve_xse_log_for_scan(
            str(data), "Fallout4", "Original", str(tmp_path / "docs")
        )
        is None
    )


def test_raises_oserror_on_operational_failure(tmp_path: Path) -> None:
    data = tmp_path / "CLASSIC Data"
    data.mkdir()
    # The YAML `\0` escape records an XSE Folder no platform can inspect.
    (data / "CLASSIC Fallout4 Local.yaml").write_text(
        'Game_Info:\n  Docs_Folder_XSE: "bad\\0xse"\n', encoding="utf-8"
    )

    with pytest.raises(OSError, match=r"^cannot inspect XSE log "):
        classic_xse.resolve_xse_log_for_scan(str(data), "Fallout4", "Original")
