"""Auxiliary domain packs must prove exact operations without owner smoke credit."""

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest
from conformance.coverage import (
    derive_row_coverage,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
)
from conformance.families.aux_operations import (
    aux_operations_coverage_policy,
    validate_aux_operations_pack,
)
from conformance.receipts import validate_prepared_run
from receipt_test_support import copy_source_inventory, prepare_receipt_case

ROOT = Path(__file__).resolve().parents[3]


def test_web_game_routing_obligates_only_adapters_with_the_public_operation():
    """URL routing cannot enroll Python or hide changed route observations."""
    from conformance.applicability import derive_applicability
    from conformance.coverage import derive_observed_fact_ids
    from conformance.packs import load_and_validate_pack

    document = load_and_validate_pack(
        ROOT, Path("tests/conformance/packs/web_operations/v1.json")
    ).document()
    route = next(
        (s for s in document["scenarios"] if s["action"] == "web-operations.routes"),
        None,
    )
    assert route is not None
    matrix = derive_applicability(document, load_source_parity_rows(ROOT))
    assert {p.id for p in matrix.participants if route["id"] in p.scenario_ids} == {
        "rust",
        "node",
        "cxx",
    }
    policy = aux_operations_coverage_policy("web-operations")
    assert derive_observed_fact_ids(document, route, route["expected"], policy)
    changed = copy.deepcopy(route["expected"])
    changed["urls"][0] = "https://wrong.invalid"
    assert not derive_observed_fact_ids(document, route, changed, policy)


@pytest.mark.parametrize("participant", ["rust", "node", "python"])
def test_resource_file_inventory_detects_mutation(
    tmp_path: Path, participant: str
) -> None:
    """Deleted, modified and unexpected files invalidate otherwise correct results."""
    pack, run, receipt = prepare_receipt_case(
        ROOT,
        tmp_path,
        Path("tests/conformance/packs/resource_operations/v1.json"),
        participant,
        runner_id="resource-effects-test",
    )
    files = receipt["scenarios"][0]["observation"]["files"]
    assert files == [
        {"path": "mods/A.esp", "hex": "706c7567696e"},
        {"path": "notes.unknown", "hex": "69676e6f726564"},
        {"path": "textures/body.dds", "hex": "44445320"},
    ]
    for replacement in (
        files[:-1],
        [{**files[0], "hex": "00"}, *files[1:]],
        [*files, {"path": "unexpected.txt", "hex": "01"}],
    ):
        changed = copy.deepcopy(receipt)
        changed["scenarios"][0]["observation"]["files"] = replacement
        run.receipt_path.write_text(json.dumps(changed))
        report = validate_prepared_run(
            pack,
            run,
            coverage_policy=aux_operations_coverage_policy("resource-operations"),
        )
        assert report.scenarios[0].result == "fail"


@pytest.mark.parametrize(
    "family", ["web-operations", "resource-operations", "version-operations"]
)
def test_auxiliary_fixture_and_predicate_contract(family: str) -> None:
    """Verify authored input separation and reject incomplete operation evidence."""
    pack = json.loads(
        (
            ROOT / "tests/conformance/packs" / family.replace("-", "_") / "v1.json"
        ).read_text()
    )
    paths = validate_aux_operations_pack(pack, ROOT)
    assert len(paths) == len(pack["scenarios"])
    for path in paths:
        assert "expected" not in json.loads(path.read_text())
    policy = aux_operations_coverage_policy(family)
    if family == "web-operations":
        from retirement_readiness import candidate_predicates

        rows = load_source_parity_rows(ROOT)
        for obligation in (
            "parity:cxx:7d9536f46f7a602a",
            "parity:cxx:1c07ae6197b62a4e",
            "parity:node:aux-phase4b-get-mod-site-name",
            "parity:node:aux-phase4b-get-mod-site-url",
            "parity:node:aux-phase4b-get-user-agent-prefix",
            "parity:node:version-registry-promote-get-classic-version",
            "parity:python:web.lib.ModSite.__eq__",
            "parity:python:web.lib.ModSite.__str__",
            "parity:python:web.lib.ModSite.__repr__",
        ):
            row = next(row for row in rows if row.obligation_id == obligation)
            assert candidate_predicates(row, pack, policy), obligation
    for predicate in policy.predicates:
        matched = [
            case["expected"]
            for case in pack["scenarios"]
            if predicate.matches(case["expected"])
        ]
        assert matched
        assert not predicate.matches({})
        assert not predicate.covers_runtime_operation("future_unobserved_operation")
        for observed in matched:
            for key in observed:
                incomplete = copy.deepcopy(observed)
                del incomplete[key]
                assert not predicate.matches(incomplete)


def test_auxiliary_validator_rejects_input_oracles() -> None:
    """An injected expected field is rejected before a native adapter runs."""
    family = "web_operations"
    pack = json.loads(
        (ROOT / "tests/conformance/packs" / family / "v1.json").read_text()
    )
    pack["scenarios"][0]["input"]["expected"] = {}
    with pytest.raises(ValueError):
        validate_aux_operations_pack(pack, ROOT)


def test_resource_pack_observes_filesystem_results_and_missing_errors() -> None:
    """Resource facts include actual traversal, size/count values and a typed miss."""
    pack = json.loads(
        (ROOT / "tests/conformance/packs/resource_operations/v1.json").read_text()
    )
    for scenario in pack["scenarios"]:
        expected = scenario["expected"]
        assert expected["resources"]
        assert expected["counts"]
        assert expected["validation"] == [
            {"path": "mods/A.esp", "error": None},
            {"path": "missing.dds", "error": "not_found"},
        ]


@pytest.mark.parametrize(
    "family,participant",
    [
        (family, participant)
        for family in ("web-operations", "resource-operations", "version-operations")
        for participant in (
            ("cxx", "node", "python")
            if family == "web-operations"
            else ("node", "python")
        )
    ],
)
def test_auxiliary_receipts_cover_selected_rows_and_reject_mutations(
    tmp_path: Path, family: str, participant: str
) -> None:
    """Source-derived obligations stay covered while altered observations and new APIs fail."""
    relative = Path("tests/conformance/packs") / family.replace("-", "_") / "v1.json"
    pack, run, receipt = prepare_receipt_case(
        ROOT, tmp_path, relative, participant, runner_id="aux-boundary-test"
    )
    policy = aux_operations_coverage_policy(family)
    report = validate_prepared_run(pack, run, coverage_policy=policy)
    assert not report.failures
    rows = load_source_parity_rows(ROOT)
    coverage = derive_row_coverage(
        pack.document(),
        rows,
        policy,
        (report,),
        scope_participant_id=participant,
        retained_analyzers=load_retained_analyzer_kinds(ROOT),
    )
    assert coverage.rows
    assert not coverage.failures
    symbols = {
        symbol
        for capability in pack.document()["capabilities"]
        for symbol in capability["rustSymbols"]
    }
    prototype = next(
        row
        for row in rows
        if row.participant_id == participant
        and row.rust_symbol in symbols
        and row.mapping_origin == "canonical_rust"
        and row.required_evidence_kind == "runtime"
    )
    added = replace(
        prototype,
        obligation_id="parity:test:future-aux-operation",
        runtime_operation="future_aux_operation",
    )
    expanded = derive_row_coverage(
        pack.document(),
        (*rows, added),
        policy,
        (report,),
        scope_participant_id=participant,
        retained_analyzers=load_retained_analyzer_kinds(ROOT),
    )
    assert [failure.obligation_id for failure in expanded.failures] == [
        added.obligation_id
    ]
    for field in receipt["scenarios"][0]["observation"]:
        changed = copy.deepcopy(receipt)
        del changed["scenarios"][0]["observation"][field]
        run.receipt_path.write_text(json.dumps(changed))
        rejected = validate_prepared_run(pack, run, coverage_policy=policy)
        assert rejected.scenarios[0].result == "fail"


@pytest.mark.parametrize("participant", ["node", "python"])
def test_source_loaded_resource_alias_cannot_borrow_class_carrier(
    tmp_path: Path, participant: str
) -> None:
    """Load a real appended public alias row; its own operation must fail closed."""
    relative = Path("tests/conformance/packs/resource_operations/v1.json")
    pack, run, _ = prepare_receipt_case(
        ROOT, tmp_path, relative, participant, runner_id="aux-alias-test"
    )
    copy_source_inventory(ROOT, tmp_path)
    contract = (
        tmp_path
        / f"docs/implementation/{participant}_api_parity/baseline/parity_contract.json"
    )
    document = json.loads(contract.read_text())
    export_key = "nodeExport" if participant == "node" else "pythonExportPath"
    current = "createResourceInfo" if participant == "node" else "parse_resource_type"
    alias = copy.deepcopy(
        next(row for row in document["tier1Mappings"] if row.get(export_key) == current)
    )
    alias["id"] = "resource-unobserved-public-alias"
    alias[export_key] = (
        "futureResourceAlias" if participant == "node" else "future_resource_alias"
    )
    document["tier1Mappings"].append(alias)
    contract.write_text(json.dumps(document))
    rows = load_source_parity_rows(tmp_path)
    added = next(
        row
        for row in rows
        if row.obligation_id == f"parity:{participant}:resource-unobserved-public-alias"
    )
    assert added.runtime_operation == "future_resource_alias"
    policy = aux_operations_coverage_policy("resource-operations")
    report = validate_prepared_run(pack, run, coverage_policy=policy)
    coverage = derive_row_coverage(
        pack.document(),
        rows,
        policy,
        (report,),
        scope_participant_id=participant,
        retained_analyzers=load_retained_analyzer_kinds(ROOT),
    )
    assert [failure.obligation_id for failure in coverage.failures] == [
        added.obligation_id
    ]
