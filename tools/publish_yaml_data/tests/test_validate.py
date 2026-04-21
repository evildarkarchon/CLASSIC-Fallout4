"""Regression tests for Windows-identity duplicate handling in YAML publish tooling."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from tools.publish_yaml_data.generate_manifest import load_ranges  # noqa: E402
from tools.publish_yaml_data.validate import load_shippable_names  # noqa: E402


def _write_schema_ranges(tmp_path: Path, names: list[str]) -> Path:
    lines = ["files:"]
    for name in names:
        lines.extend(
            [
                f'  - name: "{name}"',
                '    min_client_schema: "1.0"',
                '    max_client_schema: "1.0"',
            ]
        )
    path = tmp_path / "client-schema-ranges.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("names", "duplicate_name"),
    [
        (["CLASSIC Main.yaml", "CLASSIC Main.yaml"], "CLASSIC Main.yaml"),
        (["CLASSIC Main.yaml", "classic main.yaml"], "classic main.yaml"),
        (["CLASSIC Main.yaml", "CLASSIC Main.yaml."], "CLASSIC Main.yaml."),
        (["CLASSIC Main.yaml", "CLASSIC Main.yaml "], "CLASSIC Main.yaml "),
    ],
)
def test_range_loaders_reject_windows_identity_duplicates(
    tmp_path: Path, names: list[str], duplicate_name: str
) -> None:
    schema_ranges_path = _write_schema_ranges(tmp_path, names)

    for loader in (load_shippable_names, load_ranges):
        with pytest.raises(SystemExit) as exc_info:
            loader(schema_ranges_path)

        message = str(exc_info.value)
        assert "duplicate entry" in message
        assert duplicate_name in message


def test_load_shippable_names_preserves_original_names(tmp_path: Path) -> None:
    schema_ranges_path = _write_schema_ranges(
        tmp_path,
        ["CLASSIC Main.yaml", "CLASSIC Fallout4 Local.yaml"],
    )

    assert load_shippable_names(schema_ranges_path) == {
        "CLASSIC Main.yaml",
        "CLASSIC Fallout4 Local.yaml",
    }


def test_validate_script_reports_duplicate_entry(tmp_path: Path) -> None:
    schema_ranges_path = _write_schema_ranges(
        tmp_path,
        ["CLASSIC Main.yaml", "classic main.yaml"],
    )

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "publish_yaml_data" / "validate.py"),
            "--databases-dir",
            str(tmp_path),
            "--schema-ranges",
            str(schema_ranges_path),
        ],
        cwd=REPO_ROOT,
        text=True,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "duplicate entry" in result.stderr
    assert "classic main.yaml" in result.stderr
