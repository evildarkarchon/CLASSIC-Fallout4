"""Vocabulary transport must fail closed at the public pack/receipt seam."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from conformance.command import FAMILY_COVERAGE_POLICIES
from conformance.coverage import (
    derive_observed_fact_ids,
    derive_row_coverage,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
)
from conformance.packs import (
    PackValidationError,
    load_and_validate_pack,
    materialize_run_plan,
)
from conformance.receipts import validate_prepared_run

ROOT = Path(__file__).resolve().parents[3]
FAMILIES = ("config-vocabulary", "scan-run-vocabulary")


@pytest.mark.parametrize("family", FAMILIES)
def test_vocabulary_public_observations_require_complete_labels_and_rejection(
    family: str,
) -> None:
    """Dropping a transported label or accepting an unknown token loses coverage."""
    pack = load_and_validate_pack(
        ROOT, Path("tests/conformance/packs") / family.replace("-", "_") / "v1.json"
    )
    document = pack.document()
    policy = FAMILY_COVERAGE_POLICIES[family]
    for scenario in document["scenarios"]:
        actual = scenario["expected"]
        assert derive_observed_fact_ids(document, scenario, actual, policy)
        for mutation in (
            "omit",
            "empty-label",
            "accept-unknown",
            "duplicate",
            "extra-field",
        ):
            changed = copy.deepcopy(actual)
            if mutation == "omit":
                changed["entries"].pop(0)
            elif mutation == "empty-label":
                changed["entries"][0]["label"] = ""
            elif mutation == "accept-unknown":
                changed["entries"][-1].update(label="placeholder", rejected=False)
            elif mutation == "duplicate":
                changed["entries"].append(changed["entries"][0])
            else:
                changed["entries"][0]["claimedCoverage"] = True
            assert not derive_observed_fact_ids(document, scenario, changed, policy), (
                mutation
            )


def test_new_rust_vocabulary_variant_cannot_hide_behind_a_copied_pack(
    tmp_path: Path,
) -> None:
    """A new owner variant must fail pack loading before any adapter can run."""
    for relative in (
        "tests/conformance/packs/config_vocabulary",
        "business-logic/classic-config-core/src",
    ):
        shutil.copytree(ROOT / relative, tmp_path / relative)
    source = tmp_path / "business-logic/classic-config-core/src/installed_yaml_data.rs"
    source.write_text(
        source.read_text(encoding="utf-8").replace(
            "pub enum InstalledYamlDataProvenance {",
            "pub enum InstalledYamlDataProvenance {\n    FutureCandidate,",
        ),
        encoding="utf-8",
    )
    with pytest.raises(PackValidationError, match="Vocabulary"):
        load_and_validate_pack(
            tmp_path, Path("tests/conformance/packs/config_vocabulary/v1.json")
        )


@pytest.mark.parametrize("family", FAMILIES)
def test_vocabulary_receipts_reject_changed_wording_missing_cases_and_new_operations(
    tmp_path: Path, family: str
) -> None:
    """Only authenticated complete execution covers resolvers; wording stays exact."""
    pack_path = Path("tests/conformance/packs") / family.replace("-", "_") / "v1.json"
    for relative in (
        pack_path.parent,
        Path("business-logic/classic-config-core/src"),
        Path("business-logic/classic-scanlog-core/src/scan_run"),
        Path("business-logic/classic-durable-publication/src"),
    ):
        shutil.copytree(ROOT / relative, tmp_path / relative)
    for args in (
        ("init",),
        ("config", "user.email", "conformance@example.invalid"),
        ("config", "user.name", "Conformance Tests"),
        ("add", "."),
        ("commit", "-m", "fixture"),
    ):
        subprocess.run(
            ["git", "-C", str(tmp_path), *args], check=True, capture_output=True
        )
    pack = load_and_validate_pack(tmp_path, pack_path)
    policy = FAMILY_COVERAGE_POLICIES[family]
    for participant in ("cxx", "node", "python"):
        run = materialize_run_plan(
            pack,
            participant_id=participant,
            participant_role="semantic-adapter",
            execution_instance_id=participant,
            source_paths=(pack_path,),
        )
        plan = run.document()
        assert all("expected" not in scenario for scenario in plan["scenarios"])
        assert all(
            "label"
            not in json.dumps(scenario["input"]).replace(
                scenario["input"]["operation"], ""
            )
            for scenario in plan["scenarios"]
        )
        receipt = {
            key: plan[key]
            for key in (
                "schemaVersion",
                "familyId",
                "familyVersion",
                "expectationDigest",
                "invocation",
                "participant",
            )
        }
        receipt["runner"] = {
            "id": "test-vocabulary-boundary",
            "version": 1,
            "platform": "windows",
            "toolchain": participant,
        }
        receipt["scenarios"] = [
            {
                "id": s["id"],
                "capabilityIds": s["capabilityIds"],
                "executionStatus": "completed",
                "observation": s["expected"],
                "failure": None,
            }
            for s in pack.document()["scenarios"]
        ]
        run.receipt_path.write_text(json.dumps(receipt))
        report = validate_prepared_run(pack, run, coverage_policy=policy)
        assert not report.failures
        rows = load_source_parity_rows(ROOT)
        covered = derive_row_coverage(
            pack.document(),
            rows,
            policy,
            (report,),
            scope_participant_id=participant,
            retained_analyzers=load_retained_analyzer_kinds(ROOT),
        )
        assert covered.rows and not covered.failures
        prototype = next(
            row
            for row in rows
            if row.participant_id == participant
            and row.rust_symbol == pack.document()["capabilities"][0]["rustSymbols"][0]
        )
        new_row = replace(
            prototype,
            obligation_id="new-public-resolver",
            runtime_operation="future_label_operation",
            required_evidence_kind="runtime",
        )
        assert derive_row_coverage(
            pack.document(),
            (*rows, new_row),
            policy,
            (report,),
            scope_participant_id=participant,
            retained_analyzers=load_retained_analyzer_kinds(ROOT),
        ).failures
        for mutation in ("wording", "missing", "skipped", "stale", "extra"):
            changed = copy.deepcopy(receipt)
            if mutation == "wording":
                changed["scenarios"][0]["observation"]["entries"][0]["label"] = (
                    "changed only in Rust"
                )
            elif mutation == "missing":
                changed["scenarios"].pop()
            elif mutation == "skipped":
                changed["scenarios"][0]["executionStatus"] = "skipped"
            elif mutation == "stale":
                changed["invocation"]["id"] = "stale-invocation"
            else:
                changed["scenarios"][0]["observation"]["extra"] = True
            run.receipt_path.write_text(json.dumps(changed))
            assert validate_prepared_run(pack, run, coverage_policy=policy).failures, (
                mutation
            )


@pytest.mark.parametrize("participant", ("node", "python"))
def test_new_vocabulary_resolver_keeps_its_public_operation_identity(
    tmp_path: Path, participant: str
) -> None:
    """A new exported resolver cannot inherit coverage merely by sharing an enum."""
    for adapter in ("cxx", "node", "python"):
        relative = Path(
            f"docs/implementation/{adapter}_api_parity/baseline/parity_contract.json"
        )
        (tmp_path / relative).parent.mkdir(parents=True)
        shutil.copyfile(ROOT / relative, tmp_path / relative)
    path = (
        tmp_path
        / f"docs/implementation/{participant}_api_parity/baseline/parity_contract.json"
    )
    document = json.loads(path.read_text())
    row = next(
        row
        for row in document["tier1Mappings"]
        if row.get("rustSymbol") == "InstalledYamlDataProvenance"
    )
    added = {
        **row,
        "id": "future-resolver",
        "nodeExport": "futureLabelOperation",
        "pythonExportPath": "future_label_operation",
    }
    document["tier1Mappings"].append(added)
    path.write_text(json.dumps(document))
    actual = next(
        row
        for row in load_source_parity_rows(tmp_path)
        if row.obligation_id == f"parity:{participant}:future-resolver"
    )
    assert actual.runtime_operation == "future_label_operation"
