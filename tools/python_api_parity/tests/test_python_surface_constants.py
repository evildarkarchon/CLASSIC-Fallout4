"""The maintained Python surface includes public module variables."""

from __future__ import annotations

from pathlib import Path

import generate_baseline as baseline


def test_top_level_stub_constants_are_inventory_names(
    tmp_path: Path, monkeypatch,
) -> None:
    """Annotated module variables are recorded without mistaking prose for names."""
    stub = tmp_path / "classic_example.pyi"
    stub.write_text(
        '"""Architecture:\nA compact example.\n"""\n'
        '__version__: str\n'
        'LIMIT: int\n'
        'class Example:\n    value: int\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(baseline, "PYTHON_TARGET_MODULES", {"classic_example": stub.name})
    monkeypatch.setattr(baseline, "PYTHON_OWNER_BY_MODULE", {"classic_example": "shared"})

    manifest = baseline.parse_python_surface(tmp_path, set())
    constants = {
        (item["module"], item["export_path"], item["kind"])
        for item in manifest["exports"]
        if item["kind"] == "constant"
    }

    assert constants == {
        ("classic_example", "__version__", "constant"),
        ("classic_example", "LIMIT", "constant"),
    }
