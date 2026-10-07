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
from conformance.families.installation_paths import (
    LOCATE_CANDIDATES,
    validate_installation_paths_pack,
)
from conformance.packs import load_and_validate_pack
from conformance.receipts import validate_prepared_run

from receipt_test_support import prepare_receipt_case

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("tests/conformance/packs/installation_paths/v1.json")


def test_installation_validation_calls_are_explicitly_owned() -> None:
    """Only invoked native validation and per-file diagnostic operations get credit."""
    for operation in (
            "parse_xse_log",
            "PathValidator.validate_custom_scan_path",
            "docs_checker_validate_ini_file",
            "validateSettingsPaths",
            "path_validate_is_file",
            "check_restricted_path",
            "has_issue",
            "removeReadonly",
            "remove_readonly",
            "isValidPath",
            "validateRequiredFiles",
    ):
        assert any(
            predicate.covers_runtime_operation(operation)
            for predicate in POLICY.predicates
        )


def test_installation_paths_require_all_applicable_adapters():
    """Cached methods exist in every adapter, including both supported CXX instances."""
    pack = load_and_validate_pack(ROOT, PACK).document()
    matrix = derive_applicability(pack, load_source_parity_rows(ROOT))
    assert {p.id for p in matrix.participants} == {"rust", "cxx", "node", "python"}
    assert next(
        p for p in matrix.participants if p.id == "cxx"
    ).execution_instance_ids == ("windows-clang-cl", "windows-msvc")
    assert enforcement_for_family("installation-paths") == "blocking"


def test_installation_receipt_covers_only_the_invoked_cxx_validators(tmp_path):
    """An added shared validator must not enroll unexecuted bridge aliases."""
    pack, run, _ = prepare_receipt_case(
        ROOT, tmp_path, PACK, "cxx", runner_id="installation-validator-scope"
    )
    report = validate_prepared_run(pack, run, coverage_policy=POLICY)
    assert not report.failures
    coverage = derive_row_coverage(
        pack.document(),
        load_source_parity_rows(ROOT),
        POLICY,
        (report,),
        scope_participant_id="cxx",
        retained_analyzers=load_retained_analyzer_kinds(ROOT),
    )
    assert not coverage.failures
    assert any(
        predicate.covers_runtime_operation("path_validate_required_files")
        for predicate in POLICY.predicates
    )
    assert all(
        not predicate.covers_runtime_operation("validate_path")
        for predicate in POLICY.predicates
    )


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
    # A scoped family excludes unimplemented siblings; the full owner inventory
    # must still require independent proof for every newly exported method.
    full_owner = pack.document()
    for capability in full_owner["capabilities"]:
        capability.pop("operationScoped", None)
    failures = derive_row_coverage(
        full_owner, (*rows, future), POLICY, [report], **arguments
    ).failures
    assert future.obligation_id in {failure.obligation_id for failure in failures}


def _locate_document(tmp_path, mutate):
    """Copy the pack with only one locate scenario, applying ``mutate`` to its fixture."""
    document = load_and_validate_pack(ROOT, PACK).document()
    document["scenarios"] = [
        scenario
        for scenario in document["scenarios"]
        if scenario["id"] == "locate-first-match-wins"
    ]
    relative = Path(document["fixtureRoot"]) / document["fixtures"]["locate-first-match-wins"]
    fixture = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    mutate(document["scenarios"][0], fixture)
    destination = tmp_path / relative
    destination.parent.mkdir(parents=True)
    destination.write_text(json.dumps(fixture))
    return document


def test_locate_scenarios_cover_every_candidate_first_match_and_no_match():
    """The pack proves each of the six positions, first-match-wins and no Installation Root."""
    document = load_and_validate_pack(ROOT, PACK).document()
    located = [
        scenario["expected"]["installationRoot"]
        for scenario in document["scenarios"]
        if scenario["action"] == "installation-paths.locate"
    ]
    assert set(LOCATE_CANDIDATES) <= set(located)
    assert None in located
    first_match = next(
        scenario
        for scenario in document["scenarios"]
        if scenario["id"] == "locate-first-match-wins"
    )
    assert first_match["expected"]["installationRoot"] == "tree/work"
    assert sum(
        path.endswith("/CLASSIC Data")
        for path in first_match["expected"]["directories"]
    ) == 3


@pytest.mark.parametrize(
    "mutation", ("escape", "outside-candidate", "operation", "wrong-root", "tree")
)
def test_locate_fixture_rejects_inputs_outside_the_owned_tree(tmp_path, mutation):
    """Search starts and CLASSIC Data placements must stay inside the runner-owned tree."""

    def mutate(case, fixture):
        if mutation == "escape":
            fixture["executableDir"] = "../host/bin"
        elif mutation == "outside-candidate":
            fixture["classicDataIn"] = ["tree/elsewhere"]
        elif mutation == "operation":
            fixture["operation"] = "inspect"
        elif mutation == "wrong-root":
            case["expected"]["installationRoot"] = "tree"
        else:
            case["expected"]["directories"].remove("tree/work/install")

    document = _locate_document(tmp_path, mutate)
    with pytest.raises(ValueError):
        validate_installation_paths_pack(document, tmp_path)


@pytest.mark.parametrize("participant", ("rust", "cxx", "node", "python"))
def test_locate_receipts_reject_a_later_candidate_or_an_invented_fallback(
        tmp_path, participant
):
    """A receipt naming any root other than the first match, or a fallback, fails."""
    pack, run, receipt = prepare_receipt_case(
        ROOT, tmp_path, PACK, participant, runner_id="installation-root-test"
    )
    assert not validate_prepared_run(pack, run, coverage_policy=POLICY).failures
    index = next(
        index
        for index, scenario in enumerate(receipt["scenarios"])
        if scenario["id"] == "locate-first-match-wins"
    )
    for mutation in ("later", "fallback", "write"):
        changed = copy.deepcopy(receipt)
        observed = changed["scenarios"][index]["observation"]
        if mutation == "later":
            observed["installationRoot"] = "tree"
        elif mutation == "fallback":
            observed["installationRoot"] = "tree/build/bin"
        else:
            observed["directories"] = sorted(
                observed["directories"] + ["tree/build/bin/CLASSIC Data"]
            )
        run.receipt_path.write_text(json.dumps(changed))
        assert validate_prepared_run(pack, run, coverage_policy=POLICY).failures
