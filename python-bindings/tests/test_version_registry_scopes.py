"""Binding probes for facade-scoped Version Registry snapshots (#244).

`classic_version_registry`, `classic_version`, `classic_config`,
`classic_scangame`, and `classic_scanlog` each read the Version Registry
through their own core-owned `VersionRegistryScope` handle. A scope takes one
immutable snapshot lazily, on its first use: it searches the relative
`CLASSIC Main.yaml` locations against the working directory at that moment,
falls back to the embedded data, and never reloads.

Today every facade is a separate extension image, so these probes pass
trivially across facades; once the facades share one native library they
become the regression gate that keeps each facade's first-use snapshot lazy,
stable, and independent of another facade's root.

Each probe runs in a fresh interpreter per import order, so no order inherits
a snapshot taken by another.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_CROSS_FACADE_PROBE = r"""
import importlib
import json
import os
import sys

order = sys.argv[1].split(",")
roots = json.loads(sys.argv[2])
# Every facade is imported before any root is entered, so whatever a facade
# reports later proves its snapshot was taken at first use, not at import.
modules = {name: importlib.import_module(name) for name in order}
version_registry = modules["classic_version_registry"]
version = modules["classic_version"]
config = modules["classic_config"]
scangame = modules["classic_scangame"]
scanlog = modules["classic_scanlog"]

MAIN_YAML = 'CLASSIC_Info:\n  version: "7.31.0"\n'
GAME_YAML = 'Game_Info:\n  Main_Root_Name: "Fallout 4"\n'
IGNORE_YAML = "CLASSIC_Ignore_Fallout4: []\n"


def registry_og():
    return version_registry.VersionRegistry().get_by_id("FO4_OG").display_name


def version_knows():
    return {
        "game_163": version.is_known_fallout4_version((1, 10, 163)),
        "game_777": version.is_known_fallout4_version((1, 10, 777)),
        "game_888": version.is_known_fallout4_version((1, 10, 888)),
    }


def config_game_version():
    data = config.YamlData.from_yaml_content(
        MAIN_YAML, GAME_YAML, IGNORE_YAML, "Fallout4", "Original"
    )
    return data.game_version


def scangame_address_library():
    return scangame.AddressLibInfo.original().filename


def scanlog_plugin_limit():
    analyzer = scanlog.PluginAnalyzer([], [], "Buffout 4", "1.10.163", "1.2.72")
    return list(analyzer.check_plugin_limit(["[FF] Limit.esp"], "1.10.163", "1.36.0"))


def observe():
    return {
        "registry_og": registry_og(),
        "version": version_knows(),
        "config_game_version": config_game_version(),
        "scangame_address_library": scangame_address_library(),
        "scanlog_plugin_limit": scanlog_plugin_limit(),
    }


observed = {}

# First uses, each from a different root.
os.chdir(roots["a"])
registry_og()
config_game_version()
os.chdir(roots["b"])
version_knows()
scangame_address_library()
os.chdir(roots["empty"])
scanlog_plugin_limit()

# Stable: rewrite root A, then observe every facade from each root in turn.
with open(os.path.join(roots["a"], "CLASSIC Main.yaml"), "w", encoding="utf-8") as handle:
    handle.write(sys.argv[3])
for name in ("a", "b", "empty"):
    os.chdir(roots[name])
    observed[name] = observe()

print(json.dumps(observed))
"""

_ROOT_YAML = """Version_Registry:
  versions:
    - id: FO4_OG
      game: Fallout4
      is_vr: false
      version: "{version}"
      display_name: {display_name}
      short_name: {short_name}
      docs_name: Fallout4
      address_library:
        filename: {address_library}
        format: bin
        nexus_url: https://example.invalid/{address_library}
"""

_FACADES = (
    "classic_version_registry",
    "classic_version",
    "classic_config",
    "classic_scangame",
    "classic_scanlog",
)


def _write_root(root: Path, **fields: str) -> None:
    root.mkdir()
    (root / "CLASSIC Main.yaml").write_text(_ROOT_YAML.format(**fields), encoding="utf-8")


def _run_probe(tmp_path: Path, import_order: tuple[str, ...]) -> dict[str, dict[str, object]]:
    """Run the cross-facade probe in a fresh interpreter and return its observations."""
    roots = {"a": tmp_path / "root-a", "b": tmp_path / "root-b", "empty": tmp_path / "root-empty"}
    _write_root(
        roots["a"],
        version="1.10.555.0",
        display_name="Root A Original",
        short_name="OG",
        address_library="root-a.bin",
    )
    _write_root(
        roots["b"],
        version="1.10.777.0",
        display_name="Root B Original",
        short_name="OG",
        address_library="root-b.bin",
    )
    roots["empty"].mkdir()
    rewritten_a = _ROOT_YAML.format(
        version="1.10.888.0",
        display_name="Root A Rewritten",
        short_name="NG",
        address_library="root-a-rewritten.bin",
    )
    script = tmp_path / "version_registry_scope_probe.py"
    script.write_text(_CROSS_FACADE_PROBE, encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            ",".join(import_order),
            json.dumps({name: str(path) for name, path in roots.items()}),
            rewritten_a,
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize(
    "import_order",
    [_FACADES, tuple(reversed(_FACADES))],
    ids=["forward", "reverse"],
)
def test_each_facade_keeps_its_own_lazy_stable_snapshot(
    tmp_path: Path, import_order: tuple[str, ...]
) -> None:
    """Each facade answers from the root of its own first use, from every root."""
    observed = _run_probe(tmp_path, import_order)

    for root in ("a", "b", "empty"):
        seen = observed[root]
        # classic_version_registry and classic_config first used root A; the
        # later rewrite of root A never reloads them.
        assert seen["registry_og"] == "Root A Original", root
        assert seen["config_game_version"] == "1.10.555", root
        # classic_version and classic_scangame first used root B.
        assert seen["version"] == {"game_163": False, "game_777": True, "game_888": False}, root
        assert seen["scangame_address_library"] == "root-b.bin", root
        # classic_scanlog first used a root without YAML, so it keeps the
        # embedded registry, where 1.10.163 is OG and triggers the limit.
        assert seen["scanlog_plugin_limit"] == [True, False], root
