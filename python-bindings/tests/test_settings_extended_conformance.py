"""Native setting validation conformance through the public Python adapter."""

import json
from importlib import import_module
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACK = json.loads(
    (ROOT / "tests/conformance/packs/settings_validation/v1.json").read_text()
)


@pytest.mark.parametrize("scenario", PACK["scenarios"], ids=lambda case: case["id"])
def test_public_settings_validator_observations(scenario, monkeypatch):
    """Public coercion preserves exact values, precision, exponents and signed zero."""
    monkeypatch.syspath_prepend(str(Path(__file__).parent))
    observe_settings_extended = import_module(
        "settings_extended_conformance"
    ).observe_settings_extended
    fixture = json.loads(
        (ROOT / PACK["fixtureRoot"] / PACK["fixtures"][scenario["id"]]).read_text()
    )
    assert (
        observe_settings_extended("settings-validation", fixture)
        == scenario["expected"]
    )
