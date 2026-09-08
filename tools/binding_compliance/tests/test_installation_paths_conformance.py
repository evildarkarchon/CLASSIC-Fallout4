"""Installation receipts require controlled caches and actual public observations."""

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest
from conformance.applicability import derive_applicability
from conformance.coverage import (
    derive_row_coverage,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
)
from conformance.enforcement import enforcement_for_family
from conformance.families.installation_paths import (
    INSTALLATION_PATHS_COVERAGE_POLICY as POLICY,
)
from conformance.families.installation_paths import validate_installation_paths_pack
from conformance.packs import load_and_validate_pack
from conformance.receipts import validate_prepared_run
from receipt_test_support import prepare_receipt_case

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("tests/conformance/packs/installation_paths/v1.json")


def test_installation_paths_require_all_applicable_adapters():
    """Cached methods exist in every adapter, including both supported CXX instances."""
    pack = load_and_validate_pack(ROOT, PACK).document()
    matrix = derive_applicability(pack, load_source_parity_rows(ROOT))
    assert {p.id for p in matrix.participants} == {"rust", "cxx", "node", "python"}
    assert next(
        p for p in matrix.participants if p.id == "cxx"
    ).execution_instance_ids == ("windows-clang-cl", "windows-msvc")
    assert enforcement_for_family("installation-paths") == "blocking"


@pytest.mark.parametrize("mutation", ("missing-executable", "escape", "metadata"))
def test_installation_fixture_rejects_discovery_fallback(tmp_path, mutation):
    """Invalid caches or metadata fail before invoking any host-sensitive method."""
    document = load_and_validate_pack(ROOT, PACK).document()
    document["scenarios"] = document["scenarios"][:1]
    relative = Path(document["fixtureRoot"]) / document["fixtures"]["cached"]
    fixture = json.loads((ROOT / relative).read_text())
    if mutation == "missing-executable":
        fixture["files"] = {}
    elif mutation == "escape":
        fixture["gamePath"] = "../user-game"
    else:
        fixture["registryYaml"] = "Version_Registry: {}"
    destination = tmp_path / relative
    destination.parent.mkdir(parents=True)
    destination.write_text(json.dumps(fixture))
    with pytest.raises(ValueError):
        validate_installation_paths_pack(document, tmp_path)


@pytest.mark.parametrize("participant", ("rust", "cxx", "node", "python"))
def test_installation_receipts_reject_changed_missing_extra_and_stale_facts(
    tmp_path, participant
):
    """The authenticated comparison boundary observes paths, messages and side effects."""
    pack, run, receipt = prepare_receipt_case(
        ROOT, tmp_path, PACK, participant, runner_id="installation-boundary-test"
    )
    assert all("expected" not in case for case in run.document()["scenarios"])
    report = validate_prepared_run(pack, run, coverage_policy=POLICY)
    assert not report.failures
    for mutation in ("missing", "path", "message", "write", "directory", "stale"):
        changed = copy.deepcopy(receipt)
        observed = changed["scenarios"][0]["observation"]
        if mutation == "missing":
            del observed["docsPath"]
        elif mutation == "path":
            observed["gamePath"] = "some-other-game"
        elif mutation == "message":
            observed["checks"][0] += " invented prose"
        elif mutation == "write":
            observed["files"].append({"path": "user.ini", "content": "unexpected"})
        elif mutation == "directory":
            observed["directories"].append("unexpected")
        else:
            changed["invocation"]["id"] = "stale"
        run.receipt_path.write_text(json.dumps(changed))
        assert validate_prepared_run(pack, run, coverage_policy=POLICY).failures


@pytest.mark.parametrize("participant", ("node", "python"))
def test_installation_row_coverage_does_not_credit_unexecuted_methods(
    tmp_path, participant
):
    """Current observed methods earn coverage; future methods cannot borrow their facts."""
    pack, run, _ = prepare_receipt_case(
        ROOT, tmp_path, PACK, participant, runner_id="installation-coverage-test"
    )
    report = validate_prepared_run(pack, run, coverage_policy=POLICY)
    rows = load_source_parity_rows(ROOT)
    arguments = {
        "scope_participant_id": participant,
        "retained_analyzers": load_retained_analyzer_kinds(ROOT),
    }
    coverage = derive_row_coverage(pack.document(), rows, POLICY, [report], **arguments)
    assert not coverage.failures
    parent = next(
        row
        for row in rows
        if row.participant_id == participant and row.rust_symbol == "GamePathFinder"
    )
    future = replace(
        parent,
        obligation_id="parity:" + participant + ":future-finder",
        runtime_operation="future_discovery_method",
    )
    assert derive_row_coverage(
        pack.document(), (*rows, future), POLICY, [report], **arguments
    ).failures
