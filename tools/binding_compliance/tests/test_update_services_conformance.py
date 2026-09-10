"""Update service packs reject live endpoints and incomplete adapter observations."""

import copy
import json
from pathlib import Path

import pytest
from conformance.coverage import derive_observed_fact_ids
from conformance.families.update_services import (
    UPDATE_SERVICES_COVERAGE_POLICY,
    validate_update_services_pack,
)
from conformance.packs import load_and_validate_pack

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("tests/conformance/packs/update_services/v1.json")


def test_authored_update_results_require_status_errors_and_durable_effects():
    """A lost error or missing filesystem observation cannot grant coverage."""
    document = load_and_validate_pack(ROOT, PACK).document()
    for scenario in document["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            document, scenario, expected, UPDATE_SERVICES_COVERAGE_POLICY
        )
        changed = copy.deepcopy(expected)
        del changed["files"]
        assert not derive_observed_fact_ids(
            document, scenario, changed, UPDATE_SERVICES_COVERAGE_POLICY
        )


def test_controlled_update_inputs_reject_external_service_configuration(tmp_path):
    """A fixture cannot smuggle remote endpoints or proxy redirects to adapters."""
    document = load_and_validate_pack(ROOT, PACK).document()
    document["scenarios"] = [document["scenarios"][0]]
    reference = document["scenarios"][0]["input"]["fixtureRef"]
    relative = Path(document["fixtureRoot"]) / document["fixtures"][reference]
    fixture = json.loads((ROOT / relative).read_text())
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    fixture["service"]["pages"][0]["headers"]["Location"] = "https://example.com"
    path.write_text(json.dumps(fixture))
    with pytest.raises(ValueError, match="redirect"):
        validate_update_services_pack(document, tmp_path)
    fixture["service"]["pages"][0]["headers"].pop("Location")
    fixture["service"]["api"] = [
        {
            "status": 200,
            "headers": {},
            "body": json.dumps(
                [
                    {
                        "assets": [
                            {
                                "browser_download_url": "https://example.com/manifest.json"
                            }
                        ]
                    }
                ]
            ),
        }
    ]
    path.write_text(json.dumps(fixture))
    with pytest.raises(ValueError, match="remote asset"):
        validate_update_services_pack(document, tmp_path)


def test_update_receipts_reject_lost_error_extra_file_and_missing_execution(tmp_path):
    """Central comparison rejects semantic drift and omitted scenario obligations."""
    from conformance.receipts import validate_prepared_run
    from receipt_test_support import prepare_receipt_case

    for participant in ("rust", "cxx", "node", "python"):
        pack, run, receipt = prepare_receipt_case(
            ROOT,
            tmp_path / participant,
            PACK,
            participant,
            runner_id="update-service-boundary-test",
        )
        assert not validate_prepared_run(
            pack, run, coverage_policy=UPDATE_SERVICES_COVERAGE_POLICY
        ).failures
        mutations = []
        extra_file = copy.deepcopy(receipt)
        extra_file["scenarios"][0]["observation"]["files"].append(
            {"path": "cache/unexpected", "hex": "ff"}
        )
        mutations.append(extra_file)
        lost_error = copy.deepcopy(receipt)
        failure = next(
            case for case in lost_error["scenarios"] if case["id"] == "timeout"
        )
        failure["observation"]["results"][0]["error"] = None
        mutations.append(lost_error)
        missing = copy.deepcopy(receipt)
        missing["scenarios"].pop()
        mutations.append(missing)
        for mutation in mutations:
            run.receipt_path.write_text(json.dumps(mutation))
            report = validate_prepared_run(
                pack, run, coverage_policy=UPDATE_SERVICES_COVERAGE_POLICY
            )
            assert report.failures or any(
                case.result == "fail" for case in report.scenarios
            )
