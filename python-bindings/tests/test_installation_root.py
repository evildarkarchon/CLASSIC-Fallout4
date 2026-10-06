"""The Python projection of config's one Installation Root locator (#275)."""

from __future__ import annotations

from pathlib import Path

import classic_config


def test_locate_installation_root_returns_first_match_or_none(tmp_path: Path) -> None:
    """First candidate holding CLASSIC Data wins; no candidate means ``None``, not a fallback."""
    executable_dir = tmp_path / "build" / "bin"
    working_dir = tmp_path / "work"
    executable_dir.mkdir(parents=True)
    working_dir.mkdir()

    assert classic_config.locate_installation_root(executable_dir, working_dir) is None

    # The executable grandparent is where a development build output folder finds the
    # repository root (candidate 4).
    (tmp_path / "CLASSIC Data").mkdir()
    assert classic_config.locate_installation_root(executable_dir, working_dir) == str(tmp_path)

    # The working directory (candidate 2) wins over the grandparent.
    (working_dir / "CLASSIC Data").mkdir()
    assert classic_config.locate_installation_root(executable_dir, working_dir) == str(working_dir)

    # An omitted input skips only the candidates derived from it.
    assert classic_config.locate_installation_root(None, working_dir) == str(working_dir)
    assert classic_config.locate_installation_root(executable_dir) == str(tmp_path)
    assert classic_config.locate_installation_root() is None
