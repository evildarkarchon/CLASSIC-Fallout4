"""Binding probes for the two scoped generic YAML caches (#240).

`classic_settings` reaches the logical-key settings cache and the
path/mtime-aware YAML-file cache through its own core-owned scope handles,
while `classic_config.clear_yaml_cache()` clears the default YAML-file scope
that config's loaders use. All facades share one native
extension, so these probes are the regression gate that keeps one facade's
loads, clears, and counter resets invisible to another.

Cross-facade probes run in a fresh interpreter per import order so neither
order inherits native cache state from the other or from earlier tests.

Only the config-clear -> settings direction is observable here: no binding
exposes the default (config) scope's stats, so the reverse direction (settings
clears and resets leave the default scope alone) is pinned by the Rust probes
in `foundation/classic-shared-core/tests/yaml_cache_scopes.rs`.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import classic_settings
import pytest

_CROSS_FACADE_PROBE = r"""
import importlib
import json
import sys

order = sys.argv[1].split(",")
path = sys.argv[2]
modules = {name: importlib.import_module(name) for name in order}
settings = modules["classic_settings"]
config = modules["classic_config"]

ops = settings.YamlOperations()
ops.load_yaml_file(path)
ops.load_yaml_file(path)
loaded = settings.yaml_cache_stats()

settings.load_settings_sync("probe", path)
settings.get_cached("probe")

# The config facade owns the default YAML-file scope only.
config.clear_yaml_cache()
after_config_clear = settings.yaml_cache_stats()
logical_after_config_clear = settings.is_cached("probe")

# Settings' own clear empties its YAML-file scope but not its logical keys.
settings.clear_global_yaml_cache()
after_settings_clear = settings.yaml_cache_stats()
logical_after_settings_clear = settings.is_cached("probe")

print(json.dumps({
    "loaded": loaded,
    "after_config_clear": after_config_clear,
    "logical_after_config_clear": logical_after_config_clear,
    "after_settings_clear": after_settings_clear,
    "logical_after_settings_clear": logical_after_settings_clear,
    "logical_stats": settings.cache_stats(),
}))
"""


def _yaml_file(tmp_path: Path, name: str = "probe.yaml") -> Path:
    """Write a small mapping document under `tmp_path` and return its path."""
    path = tmp_path / name
    path.write_text("game: Fallout4\nitems:\n  - a\n  - b\n", encoding="utf-8")
    return path


def _reset_settings_scopes() -> None:
    """Empty both `classic_settings` caches and zero their counters."""
    classic_settings.clear_global_yaml_cache()
    classic_settings.reset_yaml_cache_stats()
    classic_settings.clear_cache()
    classic_settings.reset_cache_stats()


@pytest.mark.parametrize(
    "import_order",
    [
        ("classic_settings", "classic_config"),
        ("classic_config", "classic_settings"),
    ],
    ids=["settings-first", "config-first"],
)
def test_config_clear_never_touches_settings_yaml_caches(
    tmp_path: Path, import_order: tuple[str, str]
) -> None:
    """`classic_config.clear_yaml_cache()` leaves both settings scopes intact."""
    path = _yaml_file(tmp_path)
    completed = subprocess.run(
        [sys.executable, "-c", _CROSS_FACADE_PROBE, ",".join(import_order), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    observed = json.loads(completed.stdout.strip().splitlines()[-1])

    loaded = observed["loaded"]
    assert (loaded["hits"], loaded["misses"], loaded["size"]) == (1, 1, 1)
    assert loaded["capacity"] == 128

    assert observed["after_config_clear"] == loaded
    assert observed["logical_after_config_clear"] is True

    after_settings_clear = observed["after_settings_clear"]
    assert after_settings_clear["size"] == 0
    assert (after_settings_clear["hits"], after_settings_clear["misses"]) == (1, 1)
    assert observed["logical_after_settings_clear"] is True

    logical = observed["logical_stats"]
    assert (logical["hits"], logical["misses"], logical["size"]) == (1, 0, 1)
    assert logical["capacity"] == 64


def test_every_yaml_operations_object_shares_the_facade_scope(tmp_path: Path) -> None:
    """`YamlOperations.clear_cache()` empties the whole facade scope, not one object's."""
    _reset_settings_scopes()
    first_path = _yaml_file(tmp_path, "first.yaml")
    second_path = _yaml_file(tmp_path, "second.yaml")
    first = classic_settings.YamlOperations()
    second = classic_settings.YamlOperations()

    first.load_yaml_file(first_path)
    second.load_yaml_file(second_path)
    second.load_yaml_file(first_path)

    assert classic_settings.yaml_cache_stats()["size"] == 2
    assert first.get_cache_stats() == classic_settings.yaml_cache_stats()
    assert classic_settings.yaml_cache_stats()["hits"] == 1

    second.clear_cache()
    stats = classic_settings.yaml_cache_stats()
    assert stats["size"] == 0
    assert (stats["hits"], stats["misses"]) == (1, 2), "clear keeps counters"


def test_yaml_file_cache_clear_and_reset_stay_separate(tmp_path: Path) -> None:
    """Counter reset never evicts; entry clear never resets counters."""
    _reset_settings_scopes()
    path = _yaml_file(tmp_path)
    ops = classic_settings.YamlOperations()
    ops.load_yaml_file(path)
    ops.load_yaml_file(path)

    classic_settings.reset_yaml_cache_stats()
    stats = classic_settings.yaml_cache_stats()
    assert (stats["hits"], stats["misses"], stats["size"]) == (0, 0, 1)

    ops.load_yaml_file(path)
    classic_settings.clear_global_yaml_cache()
    stats = classic_settings.yaml_cache_stats()
    assert (stats["hits"], stats["misses"], stats["size"]) == (1, 0, 0)


def test_logical_key_cache_stays_distinct_from_yaml_file_cache(tmp_path: Path) -> None:
    """The two caches have separate entries, counters, and clears."""
    _reset_settings_scopes()
    path = _yaml_file(tmp_path)

    docs = classic_settings.load_settings_sync("settings_probe", str(path))
    assert docs[0]["game"] == "Fallout4"
    assert classic_settings.get_cached("settings_probe") == docs
    assert classic_settings.get_cached("absent") is None

    classic_settings.YamlOperations().load_yaml_file(path)
    assert classic_settings.yaml_cache_stats()["misses"] == 1
    logical = classic_settings.cache_stats()
    assert (logical["hits"], logical["misses"], logical["size"]) == (1, 1, 1)

    classic_settings.clear_global_yaml_cache()
    assert classic_settings.is_cached("settings_probe")

    classic_settings.YamlOperations().load_yaml_file(path)
    classic_settings.clear_cache()
    assert classic_settings.cache_size() == 0
    assert classic_settings.cache_stats()["hits"] == 1, "clear keeps counters"
    assert classic_settings.yaml_cache_stats()["size"] == 1

    classic_settings.reset_cache_stats()
    assert classic_settings.cache_stats()["hits"] == 0
    assert classic_settings.yaml_cache_stats()["misses"] == 2
