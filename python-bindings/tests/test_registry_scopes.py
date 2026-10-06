"""Binding probes for facade-scoped typed registry state (#241).

`classic_registry`, `classic_config`, and `classic_scanlog` each reach the
typed registry through their own core-owned `RegistryScope` handle, so each
facade keeps its own values and application directory. All facades share
one native extension, so these probes are the regression gate
that keeps one facade's set, clear, and exact-type key collision invisible to
another.

Each probe runs in a fresh interpreter per import order, from a script file in
a temporary directory, so import-time application-directory initialization is
observable and no order inherits native registry state from another.

`classic_scanlog` exposes no registry accessor, so its scope is pinned by the
Rust test in `classic-scanlog-py`; here it is imported to prove its
import-time initialization does not leak into the other facades.
"""

from __future__ import annotations

import itertools
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
root = sys.argv[2]
modules = {name: importlib.import_module(name) for name in order}
registry = modules["classic_registry"]
config = modules["classic_config"]

def where(name):
    return os.path.join(root, name)

observed = {
    "script_dir": os.path.dirname(os.path.abspath(__file__)),
    "initial_registry": registry.get_application_dir(),
    "initial_config": config.get_application_dir(),
}

registry.set_application_dir(where("registry"))
observed["config_after_registry_set"] = config.get_application_dir()

config.set_application_dir(where("config"))
observed["registry_after_config_set"] = registry.get_application_dir()

registry.set_game("Skyrim")
registry.clear_all()
observed["registry_after_clear"] = registry.get_application_dir()
observed["registry_game_after_clear"] = registry.get_game()
observed["config_after_registry_clear"] = config.get_application_dir()

# A generic value under the application-directory key stays a generic value:
# it is registered, readable through get(), and never the native override.
registry.register("app_dir", where("generic"))
observed["collision_registered"] = registry.is_registered("app_dir")
observed["collision_generic_get"] = registry.get("app_dir")
observed["collision_native_get"] = registry.get_application_dir()
observed["config_after_collision"] = config.get_application_dir()

# The native setter replaces the generic value; get() no longer matches it.
registry.set_application_dir(where("native"))
observed["replaced_generic_get"] = registry.get("app_dir")
observed["replaced_native_get"] = registry.get_application_dir()

registry.clear_all()
observed["config_final"] = config.get_application_dir()

print(json.dumps(observed))
"""

_FACADES = ("classic_registry", "classic_config", "classic_scanlog")


def _run_probe(tmp_path: Path, import_order: tuple[str, ...]) -> dict[str, object]:
    """Run the cross-facade probe as a script and return its observations."""
    script_dir = tmp_path / "script-dir"
    script_dir.mkdir()
    script = script_dir / "registry_scope_probe.py"
    script.write_text(_CROSS_FACADE_PROBE, encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(script), ",".join(import_order), str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize(
    "import_order",
    list(itertools.permutations(_FACADES)),
    ids=lambda order: "-".join(name.removeprefix("classic_") for name in order),
)
def test_registry_and_application_dir_stay_isolated_by_facade(
    tmp_path: Path, import_order: tuple[str, ...]
) -> None:
    """Set, get, clear, and the typed-key collision affect only their facade."""
    observed = _run_probe(tmp_path, import_order)

    def at(name: str) -> str:
        return str(tmp_path / name)

    # Import-time initialization: config registers the executed script's
    # directory in its own scope; the registry facade never auto-registers one,
    # and scanlog's initialization lands in neither facade.
    assert observed["initial_registry"] is None
    assert observed["initial_config"] == observed["script_dir"]

    assert observed["config_after_registry_set"] == observed["script_dir"]
    assert observed["registry_after_config_set"] == at("registry")

    assert observed["registry_after_clear"] is None
    assert observed["registry_game_after_clear"] == "Fallout4"
    assert observed["config_after_registry_clear"] == at("config")

    assert observed["collision_registered"] is True
    assert observed["collision_generic_get"] == at("generic")
    assert observed["collision_native_get"] is None
    assert observed["config_after_collision"] == at("config")

    assert observed["replaced_generic_get"] is None
    assert observed["replaced_native_get"] == at("native")
    assert observed["config_final"] == at("config")
