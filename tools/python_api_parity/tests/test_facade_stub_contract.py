"""Regression checks for exact maintained stub and future facade names."""

from __future__ import annotations

import json
from pathlib import Path

from validate_stubs import StubValidator

REPO_ROOT = Path(__file__).resolve().parents[3]
SURFACE_PATH = (
    REPO_ROOT
    / "docs"
    / "implementation"
    / "python_api_parity"
    / "baseline"
    / "python_api_surface.json"
)


def test_missing_and_extra_maintained_stub_names_fail() -> None:
    """The checked-in inventory must reject both directions of stub name drift."""
    stub = "class Kept: ...\nclass Added: ...\n"

    errors = StubValidator.check_stub_name_inventory(
        "classic_demo", stub, {"Kept", "Removed"}
    )

    assert any("Removed" in error and "missing" in error.lower() for error in errors)
    assert any("Added" in error and "extra" in error.lower() for error in errors)


def test_missing_and_extra_maintained_method_names_fail() -> None:
    """Class methods and properties are maintained names in the surface."""
    stub = "class Kept:\n    def added(self) -> None: ...\n"

    errors = StubValidator.check_stub_name_inventory(
        "classic_demo", stub, {"Kept", "Kept.removed"}
    )

    assert any("Kept.removed" in error and "missing" in error.lower() for error in errors)
    assert any("Kept.added" in error and "extra" in error.lower() for error in errors)


def test_missing_and_extra_source_facade_exports_fail() -> None:
    """An explicit facade ``__all__`` must match its public name contract."""
    facade = '__all__ = ["Kept", "Added"]\n'

    errors = StubValidator.check_facade_export_inventory(
        "classic_demo", facade, {"Kept", "Removed"}
    )

    assert any("Removed" in error and "missing" in error.lower() for error in errors)
    assert any("Added" in error and "extra" in error.lower() for error in errors)


def test_declared_facade_name_without_a_binding_fails() -> None:
    """A matching ``__all__`` cannot certify a missing imported or defined name."""
    errors = StubValidator.check_facade_export_inventory(
        "classic_demo", '__all__ = ["Kept"]\n', {"Kept"}
    )

    assert any("Kept" in error and "unbound" in error.lower() for error in errors)


def test_annotation_only_facade_name_is_unbound() -> None:
    """A variable annotation alone does not create a Python module attribute."""
    errors = StubValidator.check_facade_export_inventory(
        "classic_demo", 'Kept: object\n__all__ = ["Kept"]\n', {"Kept"}
    )

    assert any("Kept" in error and "unbound" in error.lower() for error in errors)


def test_dynamic_facade_export_list_fails_closed() -> None:
    """A computed ``__all__`` cannot prove exact public names from source."""
    errors = StubValidator.check_facade_export_inventory(
        "classic_demo", "__all__ = native.__all__\n", {"Kept"}
    )

    assert any("literal" in error.lower() for error in errors)


def test_merged_adapter_stubs_use_checked_in_facade_inventory(tmp_path: Path) -> None:
    """The source gate must keep checking each import after crates are merged."""
    adapter = tmp_path / "python-bindings" / "classic-python-py"
    adapter.mkdir(parents=True)
    (adapter / "classic_demo.pyi").write_text(
        '__version__: str\nclass Kept: ...\n', encoding="utf-8"
    )
    facade = adapter / "src" / "classic_demo" / "__init__.py"
    facade.parent.mkdir(parents=True)
    bound_facade = (
        '__version__ = "1.0"\n'
        'from _native import Kept\n'
        '__all__ = ["__version__", "Kept"]\n'
    )
    facade.write_text(bound_facade, encoding="utf-8")
    surface_path = (
        tmp_path
        / "docs"
        / "implementation"
        / "python_api_parity"
        / "baseline"
        / "python_api_surface.json"
    )
    surface_path.parent.mkdir(parents=True)
    surface_path.write_text(
        json.dumps(
            {
                "scope": {
                    "target_modules": ["classic_demo"],
                    "source_files": [
                        "python-bindings/classic-python-py/classic_demo.pyi"
                    ],
                },
                "exports": [
                    {"module": "classic_demo", "export": "Kept"},
                    {"module": "classic_demo", "export": "__version__"},
                ],
            }
        ),
        encoding="utf-8",
    )

    success, report = StubValidator().validate_all(tmp_path)
    assert success, report["errors"]
    assert report["total_crates"] == 1

    facade.write_text(
        '__version__ = "1.0"\n'
        'from _native import Kept, Added\n'
        '__all__ = ["__version__", "Added"]\n',
        encoding="utf-8",
    )
    success, report = StubValidator().validate_all(tmp_path)
    assert not success
    assert any("Kept" in error and "missing" in error.lower() for error in report["errors"])
    assert any("Added" in error and "extra" in error.lower() for error in report["errors"])

    facade.write_text(bound_facade, encoding="utf-8")
    (adapter / "classic_demo.pyi").write_text(
        '__version__: str\nclass Added: ...\n', encoding="utf-8"
    )
    success, report = StubValidator().validate_all(tmp_path)
    assert not success
    assert any("Kept" in error and "missing" in error.lower() for error in report["errors"])
    assert any("Added" in error and "extra" in error.lower() for error in report["errors"])


def test_current_stubs_cover_public_native_exceptions_and_dds_analyzer() -> None:
    """Maintain signatures for known live names omitted by the old source gate."""
    expected = {
        "classic_scanlog": {"RustScanLogError", "RustParseError", "RustConfigError"},
        "classic_config": {"RustConfigError", "RustConfigIOError", "RustConfigParseError"},
        "classic_database": {
            "RustDatabaseError",
            "RustDatabaseIOError",
            "RustDatabaseQueryError",
        },
        "classic_file_io": {"DDSAnalyzer"},
    }
    surface = json.loads(SURFACE_PATH.read_text(encoding="utf-8"))
    stub_paths = dict(
        zip(
            surface["scope"]["target_modules"],
            surface["scope"]["source_files"],
            strict=True,
        )
    )

    for module, names in expected.items():
        stub = (REPO_ROOT / stub_paths[module]).read_text(encoding="utf-8")
        declared = StubValidator.public_stub_names(stub)
        assert names <= declared, (module, names - declared)


def test_all_eighteen_stubs_match_checked_in_name_inventory() -> None:
    """The committed surface catches direct stub additions and removals."""
    validator = StubValidator()
    success, report = validator.validate_all(REPO_ROOT)

    assert success, report["errors"]
    assert report["total_crates"] == 18
