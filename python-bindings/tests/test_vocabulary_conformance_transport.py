"""Verify runner transport behavior without duplicating domain label expectations."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("family", "operation"),
    [
        ("config-vocabulary", "installed_yaml_data_provenance_label"),
        ("scan-run-vocabulary", "scan_run_log_disposition_label"),
    ],
)
def test_vocabulary_runner_observes_rejection_without_fixtures(
        family: str, operation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep duplicate input order and actual native rejection in the runner receipt."""
    monkeypatch.syspath_prepend(str(Path(__file__).parent))
    runner = import_module("semantic_conformance_runner")
    scenario = {
        "id": "unknown",
        "capabilityIds": [],
        "fixtureRefs": [],
        "action": "vocabulary.resolve",
        "input": {
            "operation": operation,
            "tokens": ["not_a_real_token", "not_a_real_token"],
        },
    }
    receipt = runner._scenario_receipt({"familyId": family}, scenario)
    assert receipt["executionStatus"] == "completed", receipt["failure"]
    assert receipt["observation"] == {
        "operation": operation,
        "entries": [
            {"token": "not_a_real_token", "label": None, "rejected": True},
            {"token": "not_a_real_token", "label": None, "rejected": True},
        ],
    }


def test_vocabulary_transport_rejects_carrier_defects(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not let family mismatches or malformed carriers become domain rejection."""
    monkeypatch.syspath_prepend(str(Path(__file__).parent))
    observe_vocabulary = import_module("vocabulary_conformance").observe_vocabulary
    with pytest.raises(ValueError, match="unsupported vocabulary operation for family"):
        observe_vocabulary(
            "config-vocabulary",
            {"operation": "scan_run_log_disposition_label", "tokens": []},
        )
    with pytest.raises(ValueError, match="vocabulary tokens must be non-empty strings"):
        observe_vocabulary(
            "config-vocabulary",
            {"operation": "installed_yaml_data_provenance_label", "tokens": [None]},
        )
