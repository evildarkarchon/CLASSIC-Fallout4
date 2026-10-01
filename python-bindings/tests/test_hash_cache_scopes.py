"""Binding probes for facade-scoped file-hash caches and statistics (#242).

`classic_file_io` and `classic_scangame` each hash files through their own
core-owned `FileHashScope` handle: `classic_file_io.FileHasher` owns one
cache, and Game Setup Intake runs started through `classic_scangame` hash the
game executable and XSE scripts through another. Today every facade is a
separate extension image, so these probes pass trivially across facades; once
the facades share one native library they become the regression gate that
keeps one facade's cache hits, entries, clears, and counter resets invisible
to the other.

Each probe runs in a fresh interpreter per import order, so neither order
inherits native cache state from the other or from earlier tests.

`classic_scangame` exposes no hash-cache controls, so its own scope is pinned
by the Rust test in `classic-scangame-py`; here it is driven through Game
Setup Intake to prove its hashing never reaches `classic_file_io`'s cache.
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
file_io = modules["classic_file_io"]
scangame = modules["classic_scangame"]
hasher = file_io.FileHasher

game_root = os.path.join(root, "Fallout4")
docs_root = os.path.join(root, "Docs")
os.makedirs(game_root)
os.makedirs(docs_root)
exe = os.path.join(game_root, "Fallout4.exe")
with open(exe, "wb") as handle:
    handle.write(b"not a real pe")

intake = scangame.GameSetupIntake(
    "Fallout4", "Original", game_root=game_root, docs_root=docs_root
)

def stats():
    return dict(hasher.cache_stats())

hasher.clear_cache()
hasher.reset_cache_stats()
observed = {"initial": stats()}

# classic_file_io caches the executable's hash: one miss, one entry.
observed["exe_hash"] = hasher.hash_file(exe)
observed["after_file_io_hash"] = stats()

# Game Setup Intake hashes the same executable through classic_scangame. A
# shared cache would turn that into a classic_file_io hit; a scoped one leaves
# classic_file_io's counters and entries exactly as they were.
first = scangame.run_game_setup_intake(intake)
observed["intake_status"] = first.status
observed["after_intake"] = stats()

# Clearing and resetting classic_file_io's cache must not evict what
# classic_scangame cached, and the next intake run must not repopulate
# classic_file_io's cache or move its counters.
hasher.clear_cache()
hasher.reset_cache_stats()
second = scangame.run_game_setup_intake(intake)
observed["repeat_report_matches"] = first.rendered_report == second.rendered_report
observed["after_clear_and_repeat_intake"] = stats()

# classic_file_io's own cache still works after the other facade's runs.
hasher.hash_file(exe)
hasher.hash_file(exe)
observed["final"] = stats()

print(json.dumps(observed))
"""

_FACADES = ("classic_file_io", "classic_scangame")


def _run_probe(tmp_path: Path, import_order: tuple[str, ...]) -> dict[str, object]:
    """Run the cross-facade probe as a script and return its observations."""
    script = tmp_path / "hash_scope_probe.py"
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


def _counts(stats: object) -> tuple[int, int, int]:
    """Project a `FileHasher.cache_stats()` dict to (hits, misses, size)."""
    assert isinstance(stats, dict)
    return stats["hits"], stats["misses"], stats["size"]


@pytest.mark.parametrize(
    "import_order",
    list(itertools.permutations(_FACADES)),
    ids=lambda order: "-".join(name.removeprefix("classic_") for name in order),
)
def test_hash_cache_and_statistics_stay_isolated_by_facade(
    tmp_path: Path, import_order: tuple[str, ...]
) -> None:
    """Hashing, clears, and resets in one facade never reach the other's scope."""
    observed = _run_probe(tmp_path, import_order)

    assert _counts(observed["initial"]) == (0, 0, 0)
    assert len(str(observed["exe_hash"])) == 64
    assert _counts(observed["after_file_io_hash"]) == (0, 1, 1)

    # The intake really ran (and therefore hashed the executable) ...
    assert observed["intake_status"] in {"ready", "action_required"}
    # ... without hitting, missing, or populating classic_file_io's cache.
    assert _counts(observed["after_intake"]) == (0, 1, 1)

    assert observed["repeat_report_matches"] is True
    assert _counts(observed["after_clear_and_repeat_intake"]) == (0, 0, 0)

    # One fresh miss then one hit, within classic_file_io's own scope.
    assert _counts(observed["final"]) == (1, 1, 1)
    assert observed["final"]["capacity"] == observed["initial"]["capacity"]
