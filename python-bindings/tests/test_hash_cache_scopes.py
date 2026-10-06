"""Binding probes for facade-scoped file-hash caches and statistics (#242, #259).

`classic_file_io`, `classic_scangame`, and `classic_scanlog` each hash files
through their own core-owned `FileHashScope` handle: `classic_file_io.FileHasher`
owns one cache, Game Setup Intake runs started through `classic_scangame` hash
the game executable and XSE scripts through another, and the FCX setup step of
Crash Log Scan Runs started through `classic_scanlog` hashes through a third.
All 18 facades share one native extension, so these probes are the regression
gate that keeps one facade's cache hits, entries, clears, and counter resets
invisible to the others.

Each probe runs in a fresh interpreter per import order, so neither order
inherits native cache state from the other or from earlier tests.

`classic_scangame` and `classic_scanlog` expose no hash-cache controls, so
their own scopes are pinned by Rust tests in the adapter crate
(`python-bindings/classic-python-bindings`); here they are driven through Game
Setup Intake and an FCX Crash Log Scan Run to prove their hashing never
reaches `classic_file_io`'s cache.
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


_SCANLOG_PROBE = r"""
import importlib
import json
import os
import sys

order = sys.argv[1].split(",")
root = sys.argv[2]
sys.path.insert(0, sys.argv[3])
modules = {name: importlib.import_module(name) for name in order}
file_io = modules["classic_file_io"]
scanlog = modules["classic_scanlog"]
shared = modules["classic_shared"]
hasher = file_io.FileHasher

from tests.test_scan_run_contract import _write_logs, _write_scan_run_data_root

_write_scan_run_data_root(__import__("pathlib").Path(root))
crash_log = _write_logs(__import__("pathlib").Path(root) / "selected", ["crash-fcx.log"])[0]
game_root = os.path.join(root, "Fallout4")
docs_root = os.path.join(root, "Documents")
os.makedirs(game_root)
os.makedirs(docs_root)
exe = os.path.join(game_root, "Fallout4.exe")
with open(exe, "wb") as handle:
    handle.write(b"not a real pe")

def stats():
    return dict(hasher.cache_stats())

def run_fcx_scan():
    configuration = scanlog.ScanRunConfiguration(
        installation_root=root,
        game=shared.GameId.Fallout4,
        game_version="auto",
        show_formid_values=False,
        simplify_logs=False,
        formid_database_paths=[],
    )
    request = scanlog.ScanRunRequest.targeted_with_fcx(
        configuration,
        scanlog.ScanRunTargetedSource(inputs=[str(crash_log)]),
        scanlog.ScanRunSetupContext(
            game_root=game_root, docs_root=docs_root, game_exe_path=exe
        ),
    )
    execution = scanlog.scan_run_execute(request, scanlog.ScanRunCancellation())
    assert execution.error is None, execution.error
    return execution.result.setup is not None

hasher.clear_cache()
hasher.reset_cache_stats()
observed = {"initial": stats()}

# classic_file_io caches the executable's hash: one miss, one entry.
hasher.hash_file(exe)
observed["after_file_io_hash"] = stats()

# The FCX setup step hashes the same executable through classic_scanlog's own
# scope: a shared cache would turn it into a classic_file_io hit.
observed["fcx_setup_ran"] = run_fcx_scan()
observed["after_scan"] = stats()

# After classic_file_io clears and resets, a second scan must not repopulate
# its cache or move its counters.
hasher.clear_cache()
hasher.reset_cache_stats()
run_fcx_scan()
observed["after_clear_and_repeat_scan"] = stats()

hasher.hash_file(exe)
observed["final"] = stats()
print(json.dumps(observed))
"""


@pytest.mark.parametrize(
    "import_order",
    [
        ("classic_file_io", "classic_scanlog", "classic_shared"),
        ("classic_shared", "classic_scanlog", "classic_file_io"),
    ],
    ids=["file_io-first", "scanlog-first"],
)
def test_scanlog_fcx_setup_hashes_in_its_own_scope(
    tmp_path: Path, import_order: tuple[str, ...]
) -> None:
    """An FCX Crash Log Scan Run never reaches `classic_file_io`'s hash cache."""
    script = tmp_path / "scanlog_hash_scope_probe.py"
    script.write_text(_SCANLOG_PROBE, encoding="utf-8")
    run_root = tmp_path / "run"
    run_root.mkdir()
    bindings_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, str(script), ",".join(import_order), str(run_root), str(bindings_root)],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stderr
    observed = json.loads(completed.stdout.strip().splitlines()[-1])

    assert _counts(observed["initial"]) == (0, 0, 0)
    assert _counts(observed["after_file_io_hash"]) == (0, 1, 1)
    assert observed["fcx_setup_ran"] is True
    # The scan hashed the executable without touching classic_file_io's scope.
    assert _counts(observed["after_scan"]) == (0, 1, 1)
    assert _counts(observed["after_clear_and_repeat_scan"]) == (0, 0, 0)
    # classic_scanlog's cached hash is invisible here: this is a fresh miss.
    assert _counts(observed["final"]) == (0, 1, 1)
