"""Keep every current Python binding directly importable before wheel consolidation."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest
import tomllib

from validate_stubs import StubValidator

REPO_ROOT = Path(__file__).resolve().parents[2]
SURFACE_PATH = (
    REPO_ROOT
    / "docs"
    / "implementation"
    / "python_api_parity"
    / "baseline"
    / "python_api_surface.json"
)
DIRECT_IMPORTS = (
    "classic_scanlog",
    "classic_config",
    "classic_user_settings",
    "classic_version_registry",
    "classic_database",
    "classic_file_io",
    "classic_scangame",
    "classic_registry",
    "classic_perf",
    "classic_settings",
    "classic_message",
    "classic_path",
    "classic_version",
    "classic_resource",
    "classic_xse",
    "classic_web",
    "classic_update",
    "classic_shared",
)


def maintained_stub_paths() -> dict[str, Path]:
    """Map import names to source stubs in the checked-in parity inventory."""
    surface = json.loads(SURFACE_PATH.read_text(encoding="utf-8"))
    paths = dict(
        zip(
            surface["scope"]["target_modules"],
            surface["scope"]["source_files"],
            strict=True,
        )
    )
    assert set(paths) == set(DIRECT_IMPORTS)
    return {name: REPO_ROOT / path for name, path in paths.items()}


@pytest.mark.parametrize("module_name", DIRECT_IMPORTS)
def test_direct_import_and_version(module_name: str) -> None:
    """Each import resolves and reports the version of its source wheel crate."""
    module = importlib.import_module(module_name)
    stub_path = maintained_stub_paths()[module_name]
    manifest_path = next(
        (parent / "Cargo.toml" for parent in stub_path.parents if (parent / "Cargo.toml").is_file()),
        None,
    )
    assert manifest_path is not None, stub_path
    manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))

    assert module.__version__ == manifest["package"]["version"]


@pytest.mark.parametrize("module_name", DIRECT_IMPORTS)
def test_exact_public_exports_match_maintained_stub(module_name: str) -> None:
    """Reject missing or extra public facade names, excluding typing-only records."""
    stub = maintained_stub_paths()[module_name].read_text(encoding="utf-8")
    expected = StubValidator.public_stub_names(stub) - StubValidator.typing_only_stub_names(
        stub
    ) - {"__debug_registered__"}
    facade = importlib.import_module(module_name)
    exports = facade.__all__
    assert len(exports) == len(set(exports)), module_name
    # PyO3 includes module metadata in some __all__ lists. It is not a
    # callable, class, exception, version, or maintained public constant.
    assert set(exports) - {"__doc__", "__debug_registered__"} == expected
    public_attributes = {
        name for name in dir(facade) if not name.startswith("_") and name != module_name
    }
    assert public_attributes == {name for name in expected if not name.startswith("_")}
