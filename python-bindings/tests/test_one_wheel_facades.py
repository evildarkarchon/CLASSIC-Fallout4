"""Probes for the one-wheel layout: 18 facades over one native extension (#259).

Every ``classic_*`` direct import is a pure-Python facade that re-exports the
canonical objects registered on its own native submodule,
``_classic_native._native.<facade>``. These probes run in fresh interpreters
for both facade import orders and check what a caller can observe:

* each exported name is the canonical native object, whichever facade or
  import order loaded the extension first;
* classes and exceptions keep their defining module, and every type that was
  picklable by reference stays picklable to the same object;
* values cross facades as the same Python type (``classic_shared.GameId``
  into ``classic_scanlog.ScanRunConfiguration``);
* every native async entry point schedules on CLASSIC's one shared Tokio
  runtime;
* ``classic_perf`` and ``classic_shared`` share one default metrics store,
  including clears in either direction;
* the installed environment holds only the one wheel, with no legacy
  per-module distribution or native file left behind.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ONE_WHEEL_TOOL = REPO_ROOT / "tools" / "python_wheel" / "one_wheel.py"
ADAPTER_MANIFEST = REPO_ROOT / "python-bindings" / "classic-python-bindings" / "Cargo.toml"

FACADES = (
    "classic_config",
    "classic_database",
    "classic_file_io",
    "classic_message",
    "classic_path",
    "classic_perf",
    "classic_registry",
    "classic_resource",
    "classic_scangame",
    "classic_scanlog",
    "classic_settings",
    "classic_shared",
    "classic_update",
    "classic_user_settings",
    "classic_version",
    "classic_version_registry",
    "classic_web",
    "classic_xse",
)

IMPORT_ORDERS = {
    "forward": FACADES,
    "reverse": tuple(reversed(FACADES)),
}

_IDENTITY_PROBE = r"""
import importlib
import json
import pickle
import sys

order = sys.argv[1].split(",")
modules = {name: importlib.import_module(name) for name in order}
native = sys.modules["_classic_native._native"]
observed = {"not_canonical": [], "module_mismatch": [], "pickle_failures": [],
            "picklable_types": 0, "exception_round_trips": 0}

for name, facade in modules.items():
    native_facade = sys.modules[f"_classic_native._native.{name}"]
    if getattr(native, name) is not native_facade:
        observed["not_canonical"].append(f"{name}: native attribute")
    for export in facade.__all__:
        value = getattr(facade, export)
        if value is not getattr(native_facade, export):
            observed["not_canonical"].append(f"{name}.{export}")
        if not isinstance(value, type):
            continue
        defining = value.__module__
        if defining not in ("builtins", name):
            observed["module_mismatch"].append(f"{name}.{export}: {defining}")
        if defining == name:
            # A type defined in this facade must pickle by reference to itself.
            try:
                restored = pickle.loads(pickle.dumps(value))
            except Exception as exc:
                observed["pickle_failures"].append(f"{name}.{export}: {exc!r}")
            else:
                if restored is not value:
                    observed["pickle_failures"].append(f"{name}.{export}: not identical")
                observed["picklable_types"] += 1
            if issubclass(value, BaseException):
                error = pickle.loads(pickle.dumps(value("probe")))
                if type(error) is not value or error.args != ("probe",):
                    observed["pickle_failures"].append(f"{name}.{export}: instance")
                observed["exception_round_trips"] += 1

# Cross-facade type acceptance: classic_shared's canonical GameId is the
# value classic_scanlog's configuration requires.
import classic_scanlog
import classic_shared
configuration = classic_scanlog.ScanRunConfiguration(
    installation_root=".",
    game=classic_shared.GameId.Fallout4,
    game_version="auto",
    show_formid_values=False,
    simplify_logs=False,
    formid_database_paths=[],
)
observed["cross_facade_game_id"] = configuration is not None
observed["shares_runtime"] = native._shares_classic_runtime()
observed["versions"] = {name: module.__version__ for name, module in modules.items()}
print(json.dumps(observed))
"""

_METRICS_PROBE = r"""
import importlib
import json
import sys

order = sys.argv[1].split(",")
modules = {name: importlib.import_module(name) for name in order}
perf = modules["classic_perf"]
monitor = modules["classic_shared"].RustPerformanceMonitor()
observed = {}

perf.clear_metrics()
perf.record_timing("through_perf", 0.004)
observed["monitor_sees_perf"] = monitor.get_operation_stats("through_perf")

monitor.record_metric("through_shared", 6, 128)
summary = perf.get_summary()["through_shared"]
observed["perf_sees_shared"] = [summary.count, summary.total]

monitor.clear_metrics()
observed["perf_after_shared_clear"] = sorted(perf.get_summary())

perf.record_timing("again", 0.001)
monitor.record_metric("bytes", 1, 64)
perf.clear_metrics()
observed["monitor_after_perf_clear"] = monitor.get_all_stats()
print(json.dumps(observed))
"""


def _run(script: str, tmp_path: Path, *args: str) -> dict[str, object]:
    """Run one probe in a fresh interpreter and return its JSON observations."""
    path = tmp_path / "probe.py"
    path.write_text(script, encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(path), *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])


def _adapter_version() -> str:
    """The one wheel's version, which every facade reports as ``__version__``."""
    import tomllib

    manifest = tomllib.loads(ADAPTER_MANIFEST.read_text(encoding="utf-8"))
    return manifest["package"]["version"]


@pytest.mark.parametrize("order", IMPORT_ORDERS.values(), ids=IMPORT_ORDERS.keys())
def test_facades_export_canonical_native_objects_in_either_import_order(
    tmp_path: Path, order: tuple[str, ...]
) -> None:
    observed = _run(_IDENTITY_PROBE, tmp_path, ",".join(order))

    assert observed["not_canonical"] == []
    assert observed["module_mismatch"] == []
    assert observed["pickle_failures"] == []
    # Exceptions and module-qualified classes are pickled by reference.
    assert observed["picklable_types"] >= 60
    assert observed["exception_round_trips"] >= 50
    assert observed["cross_facade_game_id"] is True
    assert observed["shares_runtime"] is True
    assert observed["versions"] == {name: _adapter_version() for name in order}


@pytest.mark.parametrize(
    "order",
    [("classic_perf", "classic_shared"), ("classic_shared", "classic_perf")],
    ids=["perf-first", "shared-first"],
)
def test_perf_and_shared_views_share_one_default_metrics_store(
    tmp_path: Path, order: tuple[str, ...]
) -> None:
    observed = _run(_METRICS_PROBE, tmp_path, ",".join(order))

    seen = observed["monitor_sees_perf"]
    assert seen is not None and seen["count"] == 1 and seen["total_ms"] == 4
    assert observed["perf_sees_shared"] == [1, pytest.approx(0.006)]
    # Clearing either view clears timing and byte state for both.
    assert observed["perf_after_shared_clear"] == []
    assert observed["monitor_after_perf_clear"] == {}


def test_native_async_entry_points_share_the_classic_runtime(tmp_path: Path) -> None:
    """Every PyO3 coroutine runs on the shared runtime, and one really completes.

    Successful awaits alone cannot tell two runtimes apart, so the structural
    check compares PyO3's scheduling runtime with the shared-core runtime.
    """
    import asyncio

    import classic_settings
    from _classic_native import _native

    assert _native._shares_classic_runtime() is True
    document = tmp_path / "probe.yaml"
    document.write_text("probe: 1\n", encoding="utf-8")

    async def load() -> object:
        return await classic_settings.load_settings_async("one-wheel-probe", str(document))

    assert asyncio.run(load()) == [{"probe": 1}]
    assert _native._shares_classic_runtime() is True


def test_installed_environment_holds_only_the_one_wheel() -> None:
    """No legacy per-module wheel or native file can make an import pass."""
    completed = subprocess.run(
        [
            sys.executable,
            str(ONE_WHEEL_TOOL),
            "verify",
            "--expected-version",
            _adapter_version(),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    report = json.loads(completed.stdout)

    assert completed.returncode == 0, report["errors"]
    assert report["ok"] is True
    assert sorted(report["facades"]) == sorted(FACADES)
    assert Path(report["native"]).parent.name == "_classic_native"


def test_remove_obsolete_clears_legacy_wheels_without_touching_others(
    tmp_path: Path,
) -> None:
    """The upgrade step deletes legacy recorded files and stray native modules."""
    sys.path.insert(0, str(ONE_WHEEL_TOOL.parent))
    try:
        import one_wheel
    finally:
        sys.path.remove(str(ONE_WHEEL_TOOL.parent))

    site = tmp_path / "site-packages"
    legacy = site / "classic_config"
    legacy.mkdir(parents=True)
    for name in ("__init__.py", "__init__.pyi", "py.typed", "classic_config.pyd"):
        (legacy / name).write_text("", encoding="utf-8")
    dist_info = site / "classic_config_py-9.1.0.dist-info"
    dist_info.mkdir()
    (dist_info / "RECORD").write_text(
        "\n".join(
            f"classic_config/{name},," for name in
            ("__init__.py", "__init__.pyi", "py.typed", "classic_config.pyd")
        )
        + "\nclassic_config_py-9.1.0.dist-info/RECORD,,\n",
        encoding="utf-8",
    )
    # A stray native module left by an interrupted uninstall, and an unrelated
    # package that must survive.
    (site / "classic_xse").mkdir()
    (site / "classic_xse" / "classic_xse.cp312-win_amd64.pyd").write_text("", encoding="utf-8")
    (site / "classic_xse" / "__init__.py").write_text("", encoding="utf-8")
    (site / "unrelated").mkdir()
    (site / "unrelated" / "__init__.py").write_text("", encoding="utf-8")

    removed = one_wheel.remove_obsolete(site)

    assert "classic_config_py-9.1.0.dist-info" in removed
    assert not legacy.exists()
    assert not dist_info.exists()
    assert not (site / "classic_xse" / "classic_xse.cp312-win_amd64.pyd").exists()
    assert (site / "classic_xse" / "__init__.py").exists()
    assert (site / "unrelated" / "__init__.py").exists()
    assert one_wheel.remove_obsolete(site) == []
