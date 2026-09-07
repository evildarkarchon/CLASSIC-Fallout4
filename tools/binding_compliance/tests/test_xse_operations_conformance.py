"""XSE facts preserve fixture-owned detection and missing-version sentinels."""

from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.families.xse_operations import XSE_OPERATIONS_COVERAGE_POLICY
from conformance.packs import load_and_validate_pack

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("tests/conformance/packs/xse_operations/v1.json")


def test_xse_missing_and_detected_versions_have_distinct_facts():
    """Detection sentinels cannot earn successful-version evidence."""
    document = load_and_validate_pack(ROOT, PACK).document()
    for scenario in document["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            document, scenario, expected, XSE_OPERATIONS_COVERAGE_POLICY
        )
        changed = dict(expected, loaderName="wrong.exe")
        assert not derive_observed_fact_ids(
            document, scenario, changed, XSE_OPERATIONS_COVERAGE_POLICY
        )
    for predicate in XSE_OPERATIONS_COVERAGE_POLICY.predicates:
        assert not predicate.covers_runtime_operation("resolve_xse_folder_for_scan")
        assert not predicate.covers_runtime_operation("future_xse_method")


def test_xse_validator_rejects_path_escape_and_receipt_drift(tmp_path):
    """Fixture filenames stay inside the owned root and missing detection stays material."""
    import copy
    import json

    import pytest
    from conformance.families.xse_operations import validate_xse_operations_pack
    from conformance.receipts import validate_prepared_run
    from receipt_test_support import prepare_receipt_case

    document = load_and_validate_pack(ROOT, PACK).document()
    document["scenarios"] = [document["scenarios"][0]]
    path = tmp_path / document["fixtureRoot"] / document["fixtures"]["missing"]
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"files": ["../f4se_loader.exe"]}))
    with pytest.raises(ValueError):
        validate_xse_operations_pack(document, tmp_path)
    for participant in ("cxx", "node", "python"):
        pack, run, receipt = prepare_receipt_case(
            ROOT,
            tmp_path / participant,
            PACK,
            participant,
            runner_id="xse-boundary-test",
        )
        report = validate_prepared_run(
            pack, run, coverage_policy=XSE_OPERATIONS_COVERAGE_POLICY
        )
        assert not report.failures
        assert all(item.result == "pass" for item in report.scenarios)
        changed = copy.deepcopy(receipt)
        changed["scenarios"][2]["observation"]["version"] = None
        run.receipt_path.write_text(json.dumps(changed))
        assert (
            validate_prepared_run(
                pack, run, coverage_policy=XSE_OPERATIONS_COVERAGE_POLICY
            )
            .scenarios[2]
            .result
            == "fail"
        )


def test_xse_byte_inventory_rejects_modified_and_additional_files():
    """Unchanged filenames alone cannot prove that detection preserved fixture bytes."""
    import copy

    document = load_and_validate_pack(ROOT, PACK).document()
    scenario = document["scenarios"][2]
    expected = scenario["expected"]
    assert expected["files"] == [
        {"path": "f4se_1_10_163.dll", "hex": ""},
        {"path": "f4se_loader.exe", "hex": ""},
    ]
    for modified in (True, False):
        changed = copy.deepcopy(expected)
        if modified:
            changed["files"][0]["hex"] = "00"
        else:
            changed["files"].append({"path": "unexpected.txt", "hex": ""})
        assert not derive_observed_fact_ids(
            document, scenario, changed, XSE_OPERATIONS_COVERAGE_POLICY
        )
