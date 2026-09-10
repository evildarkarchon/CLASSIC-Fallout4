"""Properties are source-visible exports with a distinct access contract."""

from pathlib import Path

import generate_baseline as gb
import pytest


@pytest.fixture
def property_surface(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Parse getters, mutators, methods, and functions from an isolated real stub."""
    monkeypatch.setattr(gb, "PYTHON_TARGET_MODULES", {"classic_config": "fixture.pyi"})
    (tmp_path / "fixture.pyi").write_text(
        """class Settings:
    @property
    def mode(self) -> str: ...
    @mode.setter
    def mode(self, value: str) -> None: ...
    @mode.deleter
    def mode(self) -> None: ...
    @property
    def enabled(self) -> bool: ...
    def update(self, value: str) -> None: ...
    @staticmethod
    def create(value: str) -> Settings: ...

def load(path: str) -> Settings: ...
""",
        encoding="utf-8",
    )
    return gb.parse_python_surface(tmp_path, set())


def test_properties_are_exported_once_without_becoming_callable_methods(
    property_surface: dict,
) -> None:
    """Setter/deleter signatures cannot overwrite or duplicate the read contract."""
    exports = property_surface["exports"]
    properties = [row for row in exports if row["kind"] == "property"]
    assert [row["export_path"] for row in properties] == [
        "Settings.enabled",
        "Settings.mode",
    ]
    assert properties[1]["signature"] == "def mode(self) -> str: ..."
    assert all("arity" not in row for row in properties)
    assert len([row for row in exports if row["export_path"] == "Settings.mode"]) == 1
    by_path = {row["export_path"]: row for row in exports}
    assert by_path["Settings.update"]["kind"] == "method"
    assert by_path["Settings.update"]["arity"] == 1
    assert by_path["Settings.create"]["arity"] == 1
    assert by_path["load"]["kind"] == "function"
    assert by_path["load"]["arity"] == 1


@pytest.mark.parametrize(
    "export_path,kind,status",
    (
        ("Settings.mode", "property", "matched"),
        ("Settings.mode", "method", "signature_mismatch"),
        ("Settings.update", "property", "signature_mismatch"),
        ("Settings.absent", "property", "missing_python"),
    ),
)
def test_parity_gate_validates_property_existence_and_kind(
    property_surface: dict, export_path: str, kind: str, status: str
) -> None:
    """A property obligation must name the actual getter and preserve its access kind."""
    contract = {
        "tier1Mappings": [
            {
                "id": "config.mode",
                "tier": "tier1",
                "ownerModule": "config",
                "rustSymbol": "mode",
                "pythonModule": "classic_config",
                "pythonExportPath": export_path,
                "pythonKind": kind,
            }
        ]
    }
    report = gb.generate_diff_report(
        contract, {"symbols": [{"symbol": "mode"}]}, property_surface
    )
    assert report["contract_results"][0]["status"] == status


def test_unmapped_property_still_requires_property_access_kind(
    property_surface: dict,
) -> None:
    """Unknown Rust ownership cannot hide a callable method replacing a property."""
    contract = {
        "tier1Mappings": [
            {
                "id": "config.mode",
                "tier": "tier1",
                "ownerModule": "config",
                "rustSymbol": None,
                "unmappedReason": "Binding-only fixture",
                "pythonModule": "classic_config",
                "pythonExportPath": "Settings.update",
                "pythonKind": "property",
            }
        ]
    }
    report = gb.generate_diff_report(contract, {"symbols": []}, property_surface)
    assert report["contract_results"][0]["status"] == "signature_mismatch"
